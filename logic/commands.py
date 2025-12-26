import time
import math
import core.config as config

class Command:
    def execute(self):
        return True

class Wait(Command):
    def __init__(self, duration):
        self.duration = float(duration)
        self.start_time = None

    def execute(self):
        if self.start_time is None:
            self.start_time = time.time()
        
        if time.time() - self.start_time >= self.duration:
            return True
        return False

class KeyPress(Command):
    def __init__(self, key_name, duration=0.1):
        self.key_name = key_name
        self.duration = float(duration)

    def execute(self):
        if config.hardware:
            key = config.job_manager.get_key(self.key_name)
            if key:
                config.hardware.press(key, self.duration)
        return True

# ==========================================================
# [핵심] 스마트 이동 명령어 (Smart MoveTo)
# ==========================================================
class MoveTo(Command):
    def __init__(self, x, y=None, tolerance=10):
        self.target_x = float(x)
        self.target_y = float(y) if y is not None else None
        self.tolerance = int(tolerance)
        self.last_jump_time = 0
        
        # === [설정: 여기서 픽셀 값을 수정하세요] ===
        self.HORIZONTAL_THRESHOLD = 200  # 이 거리보다 멀면 이동기(플점/텔포) 사용
        self.VERTICAL_THRESHOLD = 40     # 이 높이보다 차이나면 점프 시도
        self.ROPE_THRESHOLD = 300        # 이 높이보다 훨씬 높으면 로프 사용 (윗점프 대신)

    def execute(self):
        if not config.player_pos:
            return False # 내 위치 모르면 대기

        curr_x, curr_y = config.player_pos
        
        # 목표 지점의 Y좌표를 알 수 없으므로, 현재 맵 데이터에서 해당 X좌표 근처의 Y를 찾아야 함
        # 하지만 지금 구조상 MoveTo는 X좌표만 받음.
        # 따라서 Y축 이동은 '발판 높이'가 아니라 '단순 추측'이나 '수동 점프'가 필요할 수 있음.
        # [수정] Converter나 Scheduler에서 MoveTo를 만들 때 y좌표도 같이 넘겨줘야 완벽함.
        # 일단은 현재 위치의 Y와 목표 Y가 같다고 가정하거나, 인자로 y를 받도록 확장해야 함.
        # 여기서는 self.target_y 속성을 추가해서 처리하도록 구조를 잡음.
        
        # (임시) 만약 target_y가 없으면 현재 높이로 가정 (수평 이동만)
        if not hasattr(self, 'target_y'):
            self.target_y = curr_y 

        dx = self.target_x - curr_x
        dy = self.target_y - curr_y # 양수면 목표가 아래, 음수면 목표가 위

        # 1. 도착 확인 (X축만 체크)
        if abs(dx) <= self.tolerance:
            if config.hardware:
                config.hardware.release("left")
                config.hardware.release("right")
            return True

        # 2. 이동 방향 결정
        direction = "right" if dx > 0 else "left"
        move_key = config.job_manager.get_key(direction)
        
        # 3. 직업 설정 가져오기
        move_mode = "flash_jump" # 기본값
        if config.job_manager.job_data:
            move_mode = config.job_manager.job_data.get("move_mode", "flash_jump")

        # =================================================
        # [상하 이동 로직] (Y축)
        # =================================================
        # 목표가 내 머리 위(Top)에 있을 때
        if dy < -self.VERTICAL_THRESHOLD:
            # 1순위: 로프 커넥트 (거리가 아주 멀 때)
            rope_key = config.job_manager.get_key("rope")
            if rope_key and dy < -self.ROPE_THRESHOLD:
                print("[Move] 거리 멀어 로프 사용")
                config.hardware.release("left") # 이동하다 쏘면 안되므로 멈춤
                config.hardware.release("right")
                config.hardware.press(rope_key)
                time.sleep(1.5) # 올라가는 시간 대기
                return False

            # 2순위: 윗점프
            up_key = config.job_manager.get_key("up")
            jump_key = config.job_manager.get_key("jump")
            if up_key and jump_key:
                print("[Move] 윗점프 시도")
                # 윗점프 커맨드 (윗키+점프)
                config.hardware.hold(up_key)
                time.sleep(0.05)
                config.hardware.press(jump_key)
                time.sleep(0.05)
                config.hardware.press(jump_key) # 더블점프 방지용 혹은 2단점프
                time.sleep(0.05)
                config.hardware.release(up_key)
                time.sleep(0.8) # 체공 시간
                return False

        # 목표가 내 발 아래(Bottom)에 있을 때
        elif dy > self.VERTICAL_THRESHOLD:
            down_key = config.job_manager.get_key("down")
            jump_key = config.job_manager.get_key("jump")
            if down_key and jump_key:
                print("[Move] 하향점프 시도")
                config.hardware.hold(down_key)
                time.sleep(0.05)
                config.hardware.press(jump_key)
                time.sleep(0.05)
                config.hardware.release(down_key)
                time.sleep(0.8)
                return False

        # =================================================
        # [좌우 이동 로직] (X축)
        # =================================================
        if config.hardware:
            config.hardware.hold(move_key)

            # 거리가 멀면 이동기 사용
            if abs(dx) > self.HORIZONTAL_THRESHOLD:
                # 쿨타임 체크 (너무 빨리 연속 입력 방지)
                if time.time() - self.last_jump_time > 0.8: # 0.8초마다 시도
                    
                    if move_mode == "teleport":
                        # [텔레포트]
                        tele_key = config.job_manager.get_key("teleport")
                        # 텔포키가 없으면 점프키를 텔포로 간주 (설정 없을 시)
                        if not tele_key: tele_key = config.job_manager.get_key("jump")
                        
                        if tele_key:
                            config.hardware.press(tele_key)
                            self.last_jump_time = time.time()

                    else:
                        # [플래시 점프]
                        jump_key = config.job_manager.get_key("jump")
                        if jump_key:
                            config.hardware.press(jump_key) # 점프
                            time.sleep(0.08)                # 아주 잠깐 대기
                            config.hardware.press(jump_key) # 플점 발동
                            self.last_jump_time = time.time()

        return False

# ==========================================================
# 기존 커맨드들 (JumpAttack 등)
# ==========================================================
class JumpAttack(Command):
    def execute(self):
        if config.hardware:
            j = config.job_manager.get_key("jump")
            a = config.job_manager.get_key("attack")
            if j and a:
                config.hardware.press(j)
                time.sleep(0.1)
                config.hardware.press(a)
                time.sleep(0.5)
        return True

# 매핑 테이블
COMMAND_MAP = {
    "wait": Wait,
    "key": KeyPress,
    "move": MoveTo,
    "jump_attack": JumpAttack
}