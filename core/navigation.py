import time
import random
# from core.job_manager import JobManager  <-- 이제 여기서 import 안 해도 됨 (받아오니까)

class Navigator:
    # [수정] job_manager를 인자로 받습니다.
    def __init__(self, hardware, job_manager):
        self.hw = hardware
        self.job_manager = job_manager # 받아온 매니저 사용 (공유됨)
        
        # 초기 설정 로드 (이제 공유된 매니저에서 읽으므로 최신값임)
        self.update_settings()

        self.THRESHOLD_ARRIVED_X = 3
        self.THRESHOLD_ARRIVED_Y = 5
        self.THRESHOLD_FAR = 15

    def update_settings(self):
        """ 공유된 JobManager에서 최신 설정 읽기 """
        # 파일 다시 읽기 불필요 (설정 탭이 이미 메모리를 업데이트해둠)
        self.move_type = self.job_manager.get_movement_type()
        self.jump_key = self.job_manager.get_key('jump')
        self.teleport_key = self.job_manager.get_key('teleport')
        self.rope_key = self.job_manager.get_key('rope')
        self.up_method = self.job_manager.get_up_jump_method()
        
        if self.move_type == 'teleport' and not self.teleport_key:
            self.teleport_key = self.jump_key

    def stop(self):
        self.hw.release_all()

    def move_horizontal(self, current_x, target_x):
        self.update_settings() # 움직이기 직전에 최신값 확인
        
        diff = target_x - current_x
        distance = abs(diff)

        if distance <= self.THRESHOLD_ARRIVED_X:
            self.hw.release('left')
            self.hw.release('right')
            return True 

        direction = 'right' if diff > 0 else 'left'
        opposite = 'left' if diff > 0 else 'right'
        
        self.hw.release(opposite)
        self.hw.hold(direction)

        if distance > self.THRESHOLD_FAR:
            if self.move_type == 'teleport':
                # [텔레포트]
                self.hw.press(self.teleport_key)
                time.sleep(0.12) 
            elif self.move_type == 'flash_jump':
                # [플래시 점프]
                self.hw.press(self.jump_key)
                time.sleep(0.05)
                self.hw.press(self.jump_key)
                time.sleep(0.4) 
        else:
            pass 

        return False

    def move_vertical(self, current_y, target_y):
        self.update_settings() # 최신값 확인
        
        diff = target_y - current_y 
        dist = abs(diff)

        if dist <= self.THRESHOLD_ARRIVED_Y:
            self.hw.release('up')
            self.hw.release('down')
            return True

        if self.move_type == 'teleport':
            if diff < -self.THRESHOLD_ARRIVED_Y:
                self.hw.hold('up')
                time.sleep(0.05)
                self.hw.press(self.teleport_key)
                time.sleep(0.1)
                self.hw.release('up')
                time.sleep(0.35) 
                return False
            elif diff > self.THRESHOLD_ARRIVED_Y:
                self.hw.hold('down')
                time.sleep(0.05)
                self.hw.press(self.teleport_key)
                time.sleep(0.1)
                self.hw.release('down')
                time.sleep(0.35)
                return False
            return False

        else:
            if diff < -self.THRESHOLD_ARRIVED_Y: 
                if diff < -100 and self.rope_key:
                     self.hw.release_all()
                     time.sleep(0.1)
                     self.hw.press(self.rope_key)
                     time.sleep(1.2)
                     return False

                self.hw.release_all()
                time.sleep(0.05)
                if self.up_method == 'command':
                    self.hw.press(self.jump_key) 
                    time.sleep(0.05) 
                    self.hw.hold('up')
                    time.sleep(0.05)
                    self.hw.press(self.jump_key)
                    time.sleep(0.1)
                    self.hw.release('up')
                    time.sleep(0.6) 
                return False

            elif diff > 30: 
                self.hw.hold('down')
                time.sleep(0.05)
                self.hw.press(self.jump_key)
                time.sleep(0.1)
                self.hw.release('down')
                time.sleep(0.5)

        return False