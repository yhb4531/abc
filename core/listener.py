import keyboard
import time
import threading
import core.config as config

class KeyboardListener:
    def __init__(self):
        self.running = True
        self.thread = threading.Thread(target=self.loop)
        self.thread.daemon = True # 메인 프로그램 종료 시 같이 종료됨

    def start(self):
        self.thread.start()

    def loop(self):
        print("[Listener] 키보드 감지 시작 (F5: 시작/정지, F6: 좌표 기록)")
        
        # 핫키 등록
        keyboard.add_hotkey('f5', self.on_toggle_start)
        keyboard.add_hotkey('f6', self.on_record_position)
        
        # 스레드 유지
        keyboard.wait() 

    def on_toggle_start(self):
        """ F5를 눌렀을 때 실행 """
        # GUI의 toggle_start 함수를 원격으로 호출하여 싱크를 맞춤
        if config.gui and hasattr(config.gui, 'tab_home'):
            # 메인 스레드 충돌 방지를 위해 약간의 텀을 둠
            print("[Listener] F5 입력 감지 -> 토글 실행")
            config.gui.tab_home.toggle_start()

    def on_record_position(self):
        """ F6을 눌렀을 때 실행 (좌표 로깅) """
        if config.player_pos:
            x, y = config.player_pos
            print(f"[Record] 현재 좌표: x={x}, y={y}")
            # 나중에 여기에 파일 저장 로직 추가 가능
        else:
            print("[Record] 플레이어 위치를 찾을 수 없습니다.")

    def stop(self):
        keyboard.unhook_all()