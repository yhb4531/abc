import time
import random
import winsound # 소리 사용
from logic.combat import CombatSystem
from logic.rune import RuneManager
from logic.summon import SummonManager
from logic.utils import get_human_delay, get_jitter

class BaseHunting:
    def __init__(self, hardware, vision, navigator, job_manager):
        self.hw = hardware
        self.vision = vision
        self.nav = navigator
        self.combat = CombatSystem(hardware, job_manager)
        
        self.rune_mgr = RuneManager(vision, navigator, self.combat)
        self.summon_mgr = SummonManager(hardware, vision, navigator, self.combat)

        self.is_running = False
        self.is_paused = False
        self.state = "IDLE"
        
        self.next_break_time = 0
        self.break_duration = 0
        self.is_taking_break = False
        
        self.rune_missing_start_time = 0

    def start(self):
        self.is_running = True
        self.is_paused = False
        self.rune_mgr.reset()
        self.summon_mgr.reset()
        self.schedule_next_break()

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self.combat.release_attack()
        self.nav.stop()

    def pause(self):
        if not self.is_running: return
        self.is_paused = True
        self.combat.release_attack()
        self.nav.stop()

    def resume(self):
        if not self.is_running: return
        self.is_paused = False
        self.rune_mgr.reset()

    def schedule_next_break(self):
        self.next_break_time = time.time() + random.uniform(180, 420)

    def process_rune(self, player_pos):
        # 1. 룬 해결 대기
        if self.state == "RUNE_WAITING":
            detections = self.vision.detect_objects()
            has_rune = any(d['label'] == 'rune' for d in detections)
            
            if has_rune:
                self.rune_missing_start_time = 0
            else:
                if self.rune_missing_start_time == 0:
                    self.rune_missing_start_time = time.time()
                
                if time.time() - self.rune_missing_start_time > 1.5:
                    print("[Rune] 룬 해제 확인 -> 자동 재개")
                    # 알림음 (해제 완료)
                    winsound.Beep(1000, 200) 
                    self.rune_mgr.reset()
                    self.on_rune_solved() 
                    self.rune_missing_start_time = 0
            
            return True

        if self.summon_mgr.is_installing: return False

        # 2. 룬 매니저 호출
        if self.rune_mgr.try_activate():
            self.state = "RUNE_SOLVING"
            status = self.rune_mgr.step(player_pos)
            
            if status == "ARRIVED":
                print("[Rune] 도착 완료. 알림음 출력.")
                
                # [추가] 도착 알림음 (삐-삐-삐-)
                for _ in range(3):
                    winsound.Beep(2000, 300)
                    time.sleep(0.1)
                
                self.state = "RUNE_WAITING"
                self.rune_missing_start_time = 0
                
            elif status == "FAILED":
                self.rune_mgr.reset()
                self.on_rune_solved()
            return True
            
        return False

    def on_rune_solved(self):
        pass

    def check_and_process_break(self, current_state):
        current_time = time.time()
        if self.is_taking_break:
            if current_time > self.break_duration:
                print("[Human] 휴식 끝")
                self.is_taking_break = False
                self.schedule_next_break()
                return False
            return True

        if current_state in ["HUNTING", "ATTACKING"] and current_time > self.next_break_time:
            rest_time = random.uniform(3.0, 5.0)
            print(f"[Human] 잠시 대기... ({rest_time:.1f}s)")
            self.combat.release_attack()
            self.nav.stop()
            self.is_taking_break = True
            self.break_duration = current_time + rest_time
            return True
        return False