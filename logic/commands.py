import time
import random
import core.config as config

class Command:
    def execute(self):
        pass

class Wait(Command):
    """ 일정 시간 대기 """
    def __init__(self, duration):
        self.duration = float(duration)

    def execute(self):
        time.sleep(self.duration)
        return True # 완료됨

class KeyPress(Command):
    """ 키 누르기 (점프, 공격 등) """
    def __init__(self, key_name, duration=0.1):
        self.key_name = key_name
        self.duration = duration

    def execute(self):
        # Config를 통해 Hardware 모듈 접근
        if config.hardware:
            # JobManager에서 실제 키 매핑 가져오기 (예: 'jump' -> 'c')
            key = config.job_manager.get_key(self.key_name)
            if key:
                config.hardware.press(key, self.duration)
            else:
                print(f"[Command] 키 매핑 없음: {self.key_name}")
        return True

class MoveTo(Command):
    """ 특정 좌표로 이동 (단순화된 버전) """
    def __init__(self, x, tolerance=5):
        self.target_x = x
        self.tolerance = tolerance

    def execute(self):
        if not config.player_pos: return False # 플레이어 인식 실패 시 대기

        px, py = config.player_pos
        diff = self.target_x - px

        if abs(diff) <= self.tolerance:
            if config.hardware: config.hardware.release_all()
            return True # 도착

        # 이동 로직
        direction = "right" if diff > 0 else "left"
        key = config.job_manager.get_key(direction)
        if config.hardware:
            config.hardware.hold(key)
            # 점프 이동 등을 섞으려면 여기에 추가 로직 필요
        
        return False # 아직 도착 안 함 (계속 실행 필요)

# 명령어 이름 문자열을 클래스로 매핑해주는 딕셔너리
COMMAND_MAP = {
    "wait": Wait,
    "key": KeyPress,
    "move": MoveTo
}