import serial
import serial.tools.list_ports
import time
import random  # [필수] 가우스 분포용

class PicoDriver:
    def __init__(self):
        self.ser = None          
        self.port_name = None    

    def find_and_connect(self, specific_port=None):
        # 1. 수동 지정 포트 (강제 연결)
        if specific_port and specific_port != "":
            print(f"[Hardware] {specific_port} 포트에 진입을 시도합니다...")
            try:
                self.ser = serial.Serial(
                    port=specific_port, 
                    baudrate=115200, 
                    timeout=0.1, 
                    write_timeout=0.1,
                    dsrdtr=False, 
                    rtscts=False
                )
                self.ser.dtr = True
                self.ser.rts = True
                self.port_name = specific_port
                print(f"[Hardware] ✅ {specific_port} 연결 성공! (강제)")
                return True
            except Exception as e:
                print(f"[Hardware] ❌ 연결 실패: {e}")
                return False
        
        # 2. 자동 검색
        print("[Hardware] 🔌 피코 자동 검색 중...")
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            try:
                temp = serial.Serial(p.device, 115200, timeout=1.0)
                time.sleep(1.5)
                temp.write(b"WHO_ARE_YOU\n")
                if temp.readline().decode().strip() == "I_AM_PICO":
                    self.ser = temp
                    self.port_name = p.device
                    return True
                temp.close()
            except: pass
        return False

    def send(self, command):
        if self.ser and self.ser.is_open:
            try: self.ser.write(f"{command}\n".encode())
            except: pass

    # [핵심 수정] 가우스 분포 적용
    def press(self, key, duration=0.1):
        # 목표 시간(duration)을 평균으로 하고, 15% 정도의 표준편차를 둠
        # 예: 0.1초 입력 시 -> 실제로는 0.085 ~ 0.115 사이에서 종 모양 확률로 입력됨
        human_duration = random.gauss(duration, duration * 0.15)
        
        # 최소 0.04초는 보장 (너무 짧으면 씹힘)
        human_duration = max(0.04, human_duration)
        
        self.send(f"press:{key}:{human_duration:.3f}")
        
        # 키 떼고 다음 행동까지의 대기 시간도 가우스 분포 적용
        wait_time = max(0.05, human_duration)
        time.sleep(wait_time) 

    def hold(self, key):
        self.send(f"hold:{key}")

    def release(self, key):
        self.send(f"release:{key}")
    
    def release_all(self):
        for k in ['left','right','up','down','s','d','f','c','shift','alt','ctrl','space']:
            self.send(f"release:{k}")

    def close(self):
        if self.ser: self.ser.close()