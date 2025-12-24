import time
from logic.commands import COMMAND_MAP

class Machine:
    def __init__(self):
        self.commands = []      # 실행할 명령어 리스트 (Command 객체들)
        self.current_idx = 0    # 현재 실행 중인 명령어 인덱스
        self.loop = True        # 무한 반복 여부

    def set_routine(self, routine_data):
        """
        JSON 형태의 리스트를 받아 Command 객체로 변환
        예: [{"type": "move", "x": 100}, {"type": "key", "key": "jump"}]
        """
        self.commands = []
        self.current_idx = 0
        
        for item in routine_data:
            c_type = item.get("type", "").lower()
            args = item.get("args", {})
            
            if c_type in COMMAND_MAP:
                # 클래스 생성 (인자 주입)
                cmd_instance = COMMAND_MAP[c_type](**args)
                self.commands.append(cmd_instance)
            else:
                print(f"[Machine] 알 수 없는 명령어: {c_type}")

    def step(self):
        """ 주기적으로 호출되어 현재 명령어를 실행 """
        if not self.commands: return

        # 현재 명령어 가져오기
        cmd = self.commands[self.current_idx]
        
        # 명령어 실행 (True가 반환되면 완료된 것)
        is_finished = cmd.execute()
        
        if is_finished:
            self.current_idx += 1
            # 끝까지 갔으면 처음으로 (Loop)
            if self.current_idx >= len(self.commands):
                if self.loop:
                    self.current_idx = 0
                else:
                    self.current_idx = len(self.commands) - 1 # 멈춤