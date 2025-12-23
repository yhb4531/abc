import json
import os
import sys

# 분리된 모듈 임포트
from logic.stationary import StationaryHunting
from logic.portal import PortalHunting

class HuntingManager:
    def __init__(self, hardware, vision, navigator, job_manager):
        # 각각의 파일에서 불러온 클래스 사용
        self.stationary = StationaryHunting(hardware, vision, navigator, job_manager)
        self.portal = PortalHunting(hardware, vision, navigator, job_manager)
        self.current_logic = None

    def load_path(self, map_name):
        # 1. 경로 설정
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        file_path = os.path.join(base_dir, "data", "maps.json")
        
        # 2. 파일 읽기
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                data = json.load(f)
        except Exception as e:
            print(f"[Error] 파일 읽기 실패: {e}")
            return False
        
        # 3. 데이터 파싱
        points = data.get(map_name, {}).get("points", [])
        if not points: 
            print(f"[Error] '{map_name}' 맵 정보가 비어있습니다.")
            return False

        has_safe_spot = any(p['type'] == 'safe_spot' for p in points)
        has_portal = any(p['type'] == 'portal' for p in points)

        # 4. 로직 선택
        if has_portal and len([p for p in points if p['type'] == 'portal']) >= 2:
            self.current_logic = self.portal
        elif has_safe_spot:
            self.current_logic = self.stationary
        else:
            self.current_logic = None
            print("[Error] 적합한 사냥 로직을 찾을 수 없습니다.")
            return False
        
        # 5. 데이터 주입 및 결과 반환
        print(f"[System] '{map_name}' 로드 중...")
        result = self.current_logic.set_data(points)
        print(f"[System] 로드 결과: {result}")
        
        # [핵심] 여기서 True가 리턴되어야 GUI가 성공으로 인식함
        return result

    def start(self):
        if self.current_logic: self.current_logic.start()
    def stop(self):
        if self.current_logic: self.current_logic.stop()
    def pause(self):
        if self.current_logic: self.current_logic.pause()
    def resume(self):
        if self.current_logic: self.current_logic.resume()
    def step(self):
        if self.current_logic: self.current_logic.step()
    
    # GUI 프로퍼티 연동
    @property
    def is_running(self): return self.current_logic.is_running if self.current_logic else False
    @property
    def is_paused(self): return self.current_logic.is_paused if self.current_logic else False
    @property
    def state(self): return self.current_logic.state if self.current_logic else "IDLE"
    
    @property
    def summon_index(self): return getattr(self.current_logic, 'summon_index', 0)
    @property
    def summon_points(self): return getattr(self.current_logic, 'summon_points', [])
    @property
    def current_portal_idx(self): return getattr(self.current_logic, 'current_portal_idx', 0)
    @property
    def portal_points(self): return getattr(self.current_logic, 'portal_points', [])
    @property
    def cycle_start_time(self): return getattr(self.current_logic, 'cycle_start_time', 0)
    @property
    def cycle_duration(self): return getattr(self.current_logic, 'cycle_duration', 60)