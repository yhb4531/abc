from PyQt5.QtCore import QThread, pyqtSignal
import time
import core.config as config  # [신규] 설정 모듈 임포트

class GameLogicThread(QThread):
    # UI 갱신용 신호 (이미지, 좌표, 상태텍스트)
    update_signal = pyqtSignal(object, object, str)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """ 스레드 메인 루프 """
        while self.running:
            try:
                # 1. 비전 데이터 획득 (VisionSystem은 config를 통해 접근)
                if config.vision:
                    minimap_img = config.vision.get_cropped_minimap()
                    player_pos = config.vision.get_player_position()
                    
                    # [핵심] 전역 변수 업데이트 -> 다른 모든 모듈이 최신 정보를 씀
                    config.minimap_img = minimap_img
                    config.player_pos = player_pos
                else:
                    minimap_img = None
                    player_pos = None

                # 2. 봇 로직 수행
                # config.logic을 통해 접근하고, config.enabled로 실행 여부 판단
                if config.logic and config.enabled:
                    config.logic.step()
                    current_state = config.logic.state
                    config.state = current_state
                else:
                    current_state = "IDLE"
                    config.state = "IDLE"

                # 3. GUI로 데이터 전송 (UI 그리기용)
                if minimap_img is not None:
                    # 안전을 위해 복사본 전달
                    self.update_signal.emit(minimap_img.copy(), player_pos, current_state)
                
            except Exception as e:
                print(f"[Worker] 스레드 오류: {e}")
                # import traceback; traceback.print_exc() # 디버깅 필요시 주석 해제
            
            time.sleep(0.033) # 약 30 FPS

    def stop(self):
        self.running = False
        self.wait()