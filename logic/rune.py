import time
import math
import core.config as config

class RuneManager:
    def __init__(self):
        self.active = False          # 룬 해결 모드 활성화 여부
        self.step_phase = "SEARCH"   # 현재 단계 (SEARCH, MOVE, INTERACT, SOLVE)
        self.rune_pos = None         # 룬 좌표
        self.start_time = 0          # 타임아웃 계산용
        self.cooldown = 0            # 룬 탐지 쿨타임
        
        # 이동 설정 (Auto-Maple 스타일)
        self.tolerance_x = 10        # X축 허용 오차
        self.tolerance_y = 5         # Y축 허용 오차

    def check_and_activate(self):
        """ 주기적으로 룬이 있는지 확인하고 상태를 활성화 """
        if time.time() < self.cooldown: return False
        if self.active: return True
        if not config.vision: return False

        detections = config.vision.detect_objects()
        for d in detections:
            if d['label'] == 'rune':
                print(f"[Rune] 룬 발견! 좌표: ({d['x']}, {d['y']})")
                
                # 상태 초기화
                self.active = True
                self.step_phase = "MOVE"
                self.rune_pos = (d['x'], d['y2']) # y2: 발바닥 위치
                self.start_time = time.time()
                
                # 하드웨어 초기화 (이동 중이던 키 떼기)
                if config.hardware:
                    config.hardware.release_all()
                return True
        
        # 못 찾았으면 1초 뒤 다시 탐색
        self.cooldown = time.time() + 1.0
        return False

    def step(self):
        """ 룬 해결 상태 머신 (매 프레임 호출) """
        if not self.active: return

        # 타임아웃 안전장치 (15초 넘으면 포기)
        if time.time() - self.start_time > 15.0:
            print("[Rune] 시간 초과로 중단")
            self.finish("FAILED")
            return

        # 플레이어 위치 확인
        if not config.player_pos: return
        px, py = config.player_pos
        tx, ty = self.rune_pos

        # === [Phase 1] 이동 (Move & Adjust) ===
        if self.step_phase == "MOVE":
            dx = tx - px
            dy = ty - py
            
            # X축 이동
            if abs(dx) > self.tolerance_x:
                direction = "right" if dx > 0 else "left"
                if config.hardware:
                    config.hardware.hold(config.job_manager.get_key(direction))
                return # 이동 중에는 대기
            
            # X축 도착 -> 키 떼기
            if config.hardware:
                config.hardware.release("left")
                config.hardware.release("right")

            # Y축 이동 (높이 차이가 크면 점프/로프 시도)
            if abs(dy) > self.tolerance_y:
                # 룬이 위에 있으면 윗점프 시도 (간단 구현)
                if dy < -50: # 룬이 훨씬 위에 있음
                    print("[Rune] 윗점프 시도")
                    if config.hardware:
                        config.hardware.press(config.job_manager.get_key("up")) # 일단 윗키만
                        time.sleep(0.1)
                return 

            # 도착 완료
            print("[Rune] 위치 도착. 상호작용 시도")
            self.step_phase = "INTERACT"

        # === [Phase 2] 상호작용 (Interact) ===
        elif self.step_phase == "INTERACT":
            if config.hardware:
                # 채집키(Interact) 입력
                interact_key = config.job_manager.get_key("interact")
                if interact_key:
                    config.hardware.press(interact_key)
                    time.sleep(0.5) # 룬 해제 모션 대기
                else:
                    print("[Rune] 상호작용(interact) 키 설정이 없습니다.")
                    self.finish("FAILED")
                    return
            
            self.step_phase = "SOLVE"
            self.solve_start_time = time.time()

        # === [Phase 3] 화살표 풀기 (Solve) ===
        elif self.step_phase == "SOLVE":
            # Auto-Maple은 여기서 스크린샷을 찍고 텐서플로우 모델로 화살표를 판독합니다.
            # 현재는 모델 파일이 없으므로 구조만 잡아둡니다.
            
            # TODO: 추후 detection.py의 화살표 인식 모델 연결 필요
            # arrows = config.vision.detect_arrows() 
            # if arrows:
            #     for arrow in arrows:
            #         config.hardware.press(arrow)
            #     self.finish("SUCCESS")
            
            print("[Rune] 화살표 입력 대기... (자동 입력 미구현)")
            
            # 임시: 3초 대기 후 성공 처리 (사람이 칠 시간 벌어주기)
            if time.time() - self.solve_start_time > 3.0:
                self.finish("SUCCESS")

    def finish(self, status):
        """ 종료 처리 """
        print(f"[Rune] 룬 시퀀스 종료: {status}")
        self.active = False
        self.rune_pos = None
        self.cooldown = time.time() + 5.0 # 종료 후 5초간 쿨타임