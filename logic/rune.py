import time
from logic.utils import get_human_delay, get_jitter

class RuneManager:
    def __init__(self, vision, navigator, combat):
        self.vision = vision
        self.nav = navigator
        self.combat = combat
        
        self.is_active = False
        self.rune_pos = None      
        self.move_start_time = 0
        self.detection_cooldown = 0
    
    def try_activate(self):
        if time.time() < self.detection_cooldown: return False
        if self.is_active: return True

        detections = self.vision.detect_objects()
        for d in detections:
            if d['label'] == 'rune':
                # y2(발바닥) 좌표 타겟
                print(f"[Rune] 발견! 정밀 이동 시작 (x:{d['x']}, y_foot:{d['y2']})")
                self.combat.release_attack()
                self.nav.stop()
                
                self.is_active = True
                self.rune_pos = {'x': d['x'], 'y': d['y2']}
                self.move_start_time = time.time()
                return True
        
        self.detection_cooldown = time.time() + 0.5
        return False

    def step(self, player_pos):
        if not self.is_active or not self.rune_pos:
            self.is_active = False
            return "FAILED"

        # 1. 룬 소멸 감지 (Stuck 방지)
        detections = self.vision.detect_objects()
        rune_exists = False
        player_feet_y = player_pos[1] + 30 
        
        for d in detections:
            if d['label'] == 'rune':
                rune_exists = True
                self.rune_pos['x'] = d['x']
                self.rune_pos['y'] = d['y2']
            elif d['label'] in ['char', 'player', 'me']:
                player_feet_y = d['y2']

        if not rune_exists:
            if time.time() - self.move_start_time > 2.0:
                print("[Rune] 룬 사라짐 -> 복귀")
                self.is_active = False
                return "FAILED"

        curr_x = player_pos[0]
        curr_y = player_feet_y
        target_x = self.rune_pos['x']
        target_y = self.rune_pos['y']

        # [핵심] 정밀 이동 로직 (X 5px, Y 3px)

        # 1. X축 이동 (허용오차 5px)
        # 5px보다 멀면 무조건 좌우 이동만 함
        if abs(curr_x - target_x) > 5:
            self.nav.move_horizontal(curr_x, target_x)
            return "RUNNING"
        
        # 2. X축 완료 -> 멈추고 Y축 확인
        else:
            # 좌우 키 뗌 (X축 고정)
            self.nav.hw.release('left')
            self.nav.hw.release('right')
            
            # Y축 확인 (허용오차 3px)
            if abs(curr_y - target_y) <= 3:
                # X도 5px 이내, Y도 3px 이내 -> 완벽 도착
                self.nav.stop()
                print("[Rune] 정밀 도착 완료! 대기")
                self.is_active = False 
                return "ARRIVED"
            else:
                # 높이가 안 맞음 -> 윗점프/로프 등 시도
                self.nav.move_vertical(curr_y, target_y)
                return "RUNNING"

        # 타임아웃
        if time.time() - self.move_start_time > 15.0:
            self.nav.stop()
            self.is_active = False
            return "FAILED"

        return "RUNNING"

    def reset(self):
        self.is_active = False
        self.rune_pos = None