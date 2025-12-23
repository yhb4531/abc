import sys
import os
import json
import atexit 
from PyQt5.QtWidgets import QApplication

# 현재 경로 추가
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(ROOT_DIR)

from core.hardware import PicoDriver
from core.vision import VisionSystem
from gui.main_window import MainWindow

# [변경] 이름 세탁: MapleProApp -> AudioServiceApp
class AudioServiceApp:
    def __init__(self):
        # [변경] 로그 내용도 시스템 드라이버인 척 변경
        print(f"[System] 루트 경로: {ROOT_DIR}")
        print("[System] Audio Service 시스템 초기화 중...")
        
        # 1. 하드웨어
        self.hardware = PicoDriver()
        
        # 프로그램 종료 시 실행될 안전장치
        atexit.register(self.emergency_cleanup)
        
        # 2. 설정 로드
        self.settings = self.load_settings()
        target_port = self.settings.get("hardware", {}).get("com_port", "")
        if target_port:
            print(f"[System] 포트({target_port}) 연결 시도")
            self.hardware.find_and_connect(target_port)
        else:
            print("[System] 포트 설정 없음 (대기 중)")

        # 3. 비전 (모델 이름은 minimap.pt로 유지해도 내부 파일이라 안 보임)
        model_path = os.path.join(ROOT_DIR, "models", "minimap.pt")
        if os.path.exists(model_path):
            self.vision = VisionSystem(model_path)
        else:
            print(f"[Error] 드라이버 파일 없음: {model_path}") # 에러 메시지도 드라이버인 척
            self.vision = None

        # 4. GUI 실행
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        
        if self.vision:
            self.window.set_modules(self.hardware, self.vision)

    def load_settings(self):
        try:
            path = os.path.join(ROOT_DIR, "data", "settings.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return {}

    def emergency_cleanup(self):
        """ [안전장치] 종료 시 키 입력 해제 """
        print("\n[System] 서비스 종료. 리소스를 해제합니다.")
        if self.hardware:
            self.hardware.release_all()
            self.hardware.close()

    def run(self):
        self.window.show()
        try:
            sys.exit(self.app.exec_())
        except Exception as e:
            print(f"[System] 런타임 오류: {e}")
        finally:
            self.emergency_cleanup()

if __name__ == "__main__":
    # [변경] 실행 클래스 이름 변경
    launcher = AudioServiceApp()
    launcher.run()