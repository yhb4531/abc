import time
import random
from logic.base import BaseHunting
from logic.utils import get_human_delay, get_jitter

class PortalHunting(BaseHunting):
    def __init__(self, hardware, vision, navigator, job_manager):
        super().__init__(hardware, vision, navigator, job_manager)
        
        self.portal_points = []     
        self.current_portal_idx = 0       
        
        self.cycle_duration = 120.0 
        self.cycle_start_time = 0
        self.move_start_time = 0
        self.current_target = None
        self.next_move_time = 0
        self.is_holding_attack = False
        self.current_jitter_x = 0

    def set_data(self, points):
        self.summon_mgr.set_points(points)
        self.portal_points = [p for p in points if p['type'] in ['portal', 'summon']]
        real_portal_count = len([p for p in self.portal_points if p['type'] == 'portal'])
        if real_portal_count >= 2: return True
        return False

    def start(self):
        super().start()
        self.state = "INSTALL" 
        self.current_portal_idx = 0
        self.move_start_time = time.time()
        self.cycle_start_time = time.time()
        self.current_jitter_x = get_jitter(5)
        print("[Portal] 시작")

    # ==========================================
    # [수정] 룬 해제 후 복귀 로직 (안전성 강화)
    # ==========================================
    def on_rune_solved(self):
        current_time = time.time()
        elapsed = current_time - self.cycle_start_time
        
        # 1. 쿨타임이 아직 남았을 때
        if elapsed < self.cycle_duration:
            print(f"[Portal] 룬 해제 완료. 원래 경로로 복귀합니다.")
            
            # [핵심 변경] 바로 ATTACKING으로 가면 엉뚱한 곳에서 공격함.
            # INSTALL 상태로 보내서 "해당 포탈 위치로 이동"하게 만듦.
            self.state = "INSTALL"
            
            # 주의: current_portal_idx는 초기화하지 않고 그대로 둠 (가던 길 계속 감)
            self.move_start_time = time.time()
            self.current_jitter_x = 0
            
        # 2. 쿨타임이 다 됐을 때
        else:
            print("[Portal] 룬 해제 완료. 쿨타임 종료 -> 처음부터 재설치")
            self.state = "INSTALL"
            self.current_portal_idx = 0 # 처음부터 다시
            self.move_start_time = time.time()
            self.current_jitter_x = get_jitter(5)

    def step(self):
        if not self.is_running: return
        if self.is_paused: return 
        
        player_pos = self.vision.get_player_position()
        if player_pos is None: return
        curr_x, curr_y = player_pos

        if self.process_rune(player_pos): return
        if self.check_and_process_break(self.state):
            self.next_move_time = time.time() + 1.0 
            return
        
        current_time = time.time()
        
        # [상태 1] 설치 및 복귀 모드
        if self.state == "INSTALL":
            if self.current_portal_idx >= len(self.portal_points):
                # 끝까지 다 돌았으면 공격 모드로
                self.state = "ATTACKING"
                self.next_move_time = time.time() + random.gauss(3.0, 0.3)
                self.is_holding_attack = False
                # 마지막 포탈 인덱스 유지 (공격 시작점)
                self.current_portal_idx = len(self.portal_points) - 1
                return

            target = self.portal_points[self.current_portal_idx]
            if self.current_target != target:
                self.current_target = target
                self.move_start_time = time.time()
            
            target_x = target['x'] + self.current_jitter_x
            ax = self.nav.move_horizontal(curr_x, target_x)
            ay = False
            if ax: ay = self.nav.move_vertical(curr_y, target['y'])
            
            if (ax and ay) or (time.time() - self.move_start_time > 5.0):
                self.nav.stop()
                time.sleep(get_human_delay(0.5))
                
                if target['type'] == 'portal':
                    print(f"[Portal] 포탈 설치/확인 ({self.current_portal_idx + 1})")
                    self.combat.install_portal()
                    self.summon_mgr.check_and_install_immediate(player_pos)
                    
                    self.current_portal_idx += 1
                    self.move_start_time = time.time()
                    self.current_jitter_x = get_jitter(5)
                
                elif target['type'] == 'summon':
                    self.current_portal_idx += 1
                    self.move_start_time = time.time()
                    self.current_jitter_x = get_jitter(5)

        # [상태 2] 공격 및 순환
        elif self.state == "ATTACKING":
            if self.summon_mgr.check_and_install_immediate(player_pos):
                self.is_holding_attack = False
                self.next_move_time = time.time() + 2.0 
                return

            extra_delay = random.uniform(0.0, 3.0)
            if time.time() - self.cycle_start_time > (self.cycle_duration + extra_delay):
                print("[Portal] 쿨타임 종료 -> 재설치")
                self.combat.release_attack()
                self.is_holding_attack = False
                self.state = "INSTALL"
                self.current_portal_idx = 0
                self.move_start_time = time.time()
                self.cycle_start_time = time.time() 
                self.current_jitter_x = get_jitter(5)
                return

            # [수정] 3타로 변경 (약 1.85초)
            if current_time < self.next_move_time:
                if not self.is_holding_attack:
                    self.combat.hold_attack()
                    self.is_holding_attack = True
                return

            self.combat.release_attack()
            self.is_holding_attack = False
            
            time.sleep(0.25 + random.uniform(0.0, 0.15))
            self.combat.use_upper_portal()
            self.is_holding_attack = True 
            
            next_attack_duration = 1.85 + random.uniform(0.0, 0.15)
            self.next_move_time = time.time() + next_attack_duration
            
            while True:
                self.current_portal_idx = (self.current_portal_idx + 1) % len(self.portal_points)
                if self.portal_points[self.current_portal_idx]['type'] == 'portal':
                    break