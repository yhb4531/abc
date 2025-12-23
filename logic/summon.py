import time
from logic.utils import get_human_delay, get_jitter

class SummonManager:
    def __init__(self, hardware, vision, navigator, combat):
        self.hw = hardware
        self.vision = vision
        self.nav = navigator
        self.combat = combat
        
        self.summon_points = []
        self.last_install_time = 0
        self.install_cooldown = 60.0 # 쿨타임
        
        self.current_idx = 0
        self.is_installing = False
        self.move_start_time = 0
        self.current_jitter_x = 0

    def set_points(self, points):
        self.summon_points = [p for p in points if p['type'] == 'summon']

    def reset(self):
        self.current_idx = 0
        self.is_installing = False
        self.last_install_time = 0 

    # ==========================================
    # [최종] 스마트 설치 (제자리 설치 Sync)
    # ==========================================
    def check_and_install_immediate(self, player_pos):
        # 1. 쿨타임 체크
        if time.time() - self.last_install_time < self.install_cooldown:
            return False

        curr_x, curr_y = player_pos

        for i, point in enumerate(self.summon_points):
            # 오차 범위 내에 있으면 (Jitter 포함된 위치라도 OK)
            if abs(curr_x - point['x']) <= 15 and abs(curr_y - point['y']) <= 10:
                print(f"[Summon] 스마트 감지! 현재 위치에서 즉시 설치")
                
                # 행동 중단
                self.combat.release_attack()
                self.nav.stop()
                time.sleep(0.5)

                # [핵심] 이동 없이 그 자리에서 바로 설치
                self.combat.use_summon_at_index(i)
                self.last_install_time = time.time()
                time.sleep(0.6) # 설치 후딜레이
                
                return True
        
        return False

    # (제자리 사냥용 순차 설치 로직 - 기존 유지)
    def start_install_sequence(self):
        if not self.summon_points: return False
        self.is_installing = True
        self.current_idx = 0
        self.move_start_time = time.time()
        self.current_jitter_x = get_jitter(5)
        return True

    def step_sequence(self, player_pos):
        if not self.is_installing: return "DONE"
        if self.current_idx >= len(self.summon_points):
            self.is_installing = False
            return "DONE"

        target = self.summon_points[self.current_idx]
        curr_x, curr_y = player_pos
        
        target_x = target['x'] + self.current_jitter_x
        ax = self.nav.move_horizontal(curr_x, target_x)
        ay = False
        if ax: ay = self.nav.move_vertical(curr_y, target['y'])

        if (ax and ay) or (time.time() - self.move_start_time > 5.0):
            self.nav.stop()
            self.combat.use_summon_at_index(self.current_idx)
            self.current_idx += 1
            self.move_start_time = time.time()
            self.current_jitter_x = get_jitter(5)
            
        return "RUNNING"