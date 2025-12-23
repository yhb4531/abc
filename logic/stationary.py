import time
from logic.base import BaseHunting
from logic.utils import get_human_delay, get_jitter

class StationaryHunting(BaseHunting):
    def __init__(self, hardware, vision, navigator, job_manager):
        super().__init__(hardware, vision, navigator, job_manager)
        
        self.safe_spot = None
        self.cycle_duration = 60.0
        self.cycle_start_time = 0
        self.last_attack_action_time = 0
        self.is_attacking = False
        self.attack_hold_duration = 10.0
        
        self.move_start_time = 0
        self.current_target = None
        self.current_jitter_x = 0

    # [핵심 추가] GUI가 summon_index를 찾을 때, 매니저의 정보를 대신 보여줌
    @property
    def summon_index(self):
        return self.summon_mgr.current_idx

    # [핵심 추가] GUI가 summon_points를 찾을 때
    @property
    def summon_points(self):
        return self.summon_mgr.summon_points

    def set_data(self, points):
        self.summon_mgr.set_points(points)
        safe_spots = [p for p in points if p['type'] == 'safe_spot']
        if safe_spots:
            self.safe_spot = safe_spots[0]
            return True
        return False

    def start(self):
        super().start()
        self.state = "SETUP"
        self.summon_mgr.start_install_sequence()
        self.cycle_start_time = time.time()
        print("[Stationary] 시작")

    def on_rune_solved(self):
        # 쿨타임 체크 (사이클 시간 비교)
        current_time = time.time()
        elapsed = current_time - self.cycle_start_time
        
        # 만약 사이클(60초)이 아직 안 지났다면? (예: 50초 남음)
        if elapsed < self.cycle_duration:
            print(f"[Stationary] 룬 해제 완료. 쿨타임 남음({int(self.cycle_duration - elapsed)}s) -> 안전지대 복귀")
            self.state = "MOVING_TO_SAFE" # 설치 건너뛰고 복귀
            # 주의: move_start_time을 초기화해줘야 복귀 로직이 정상 작동함
            self.move_start_time = time.time()
            self.current_jitter_x = get_jitter(6)
        else:
            # 쿨타임 다 됐으면 원래대로 재설치
            print("[Stationary] 룬 해제 완료. 쿨타임 종료 -> 재설치")
            self.state = "SETUP"
            self.summon_mgr.start_install_sequence()

    def step(self):
        if not self.is_running: return
        if self.is_paused: return
        
        player_pos = self.vision.get_player_position()
        if player_pos is None: return
        curr_x, curr_y = player_pos

        if self.process_rune(player_pos): return
        if self.check_and_process_break(self.state): return

        current_time = time.time()

        if self.state == "SETUP":
            status = self.summon_mgr.step_sequence(player_pos)
            if status == "DONE":
                self.state = "MOVING_TO_SAFE"
                self.move_start_time = time.time()
                self.current_jitter_x = get_jitter(15)
            return

        elif self.state == "MOVING_TO_SAFE":
            target = self.safe_spot
            if self.current_target != target:
                self.current_target = target
                self.move_start_time = time.time()

            target_x = target['x'] + self.current_jitter_x
            ax = self.nav.move_horizontal(curr_x, target_x)
            ay = False
            if ax: ay = self.nav.move_vertical(curr_y, target['y'])
            
            if (ax and ay) or (time.time() - self.move_start_time > 8.0):
                self.nav.stop()
                direction = target.get('direction')
                if direction in ['left', 'right']:
                    self.hw.press(direction, duration=0.15)
                    time.sleep(0.5)

                self.state = "HUNTING"
                self.cycle_start_time = time.time()
                self.last_attack_action_time = time.time()
                self.is_attacking = False

        elif self.state == "HUNTING":
            if current_time - self.cycle_start_time > self.cycle_duration:
                print("[Stationary] 쿨타임 종료 -> 재설치")
                self.combat.release_attack()
                self.state = "SETUP"
                self.summon_mgr.start_install_sequence()
                return

            if self.is_attacking:
                if current_time - self.last_attack_action_time > self.attack_hold_duration:
                    self.combat.release_attack()
                    self.is_attacking = False
                    self.last_attack_action_time = current_time
            else:
                if current_time - self.last_attack_action_time > 0.8:
                    self.combat.hold_attack()
                    self.is_attacking = True
                    self.last_attack_action_time = current_time