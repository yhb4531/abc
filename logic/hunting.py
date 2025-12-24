import json
import os
import sys
import core.config as config
from logic.machine import Machine
from logic.rune import RuneManager
# [중요] 스케줄러 임포트
from logic.scheduler import RoutineScheduler

class HuntingManager:
    def __init__(self, hardware, vision, navigator, job_manager):
        self.machine = Machine()
        self.rune_manager = RuneManager()
        self.scheduler = None # 스케줄러 인스턴스
        
        self.state = "IDLE"
        self.is_running = False
        self.is_paused = False
        
        # GUI 더미
        self.cycle_start_time = 0
        self.cycle_duration = 0

    def load_path(self, map_name):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        file_path = os.path.join(base_dir, "data", "maps.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                data = json.load(f)
        except Exception as e:
            print(f"[Error] 맵 파일 로드 실패: {e}")
            return False
        
        map_data = data.get(map_name, {})
        
        # === [스케줄러 초기화] ===
        if "points" in map_data:
            points = map_data["points"]
            settings = map_data.get("settings", {})
            
            # 스케줄러 생성 (쿨타임 관리 시작)
            self.scheduler = RoutineScheduler(points, settings)
            print(f"[System] 스케줄러 가동: {map_name}")
            
            # 첫 번째 루틴 생성 및 주입
            first_routine = self.scheduler.get_next_routine()
            self.machine.set_routine(first_routine)
            self.machine.loop = False # [중요] 루프 끄기 (다 하면 스케줄러한테 다시 받아야 함)
            
        elif "routine" in map_data:
            # 수동 루틴 모드 (Legacy)
            self.scheduler = None
            self.machine.set_routine(map_data["routine"])
            self.machine.loop = True
        else:
            return False

        return True

    def start(self):
        self.is_running = True
        self.is_paused = False
        self.state = "HUNTING"
        print("[Logic] 사냥 시작")

    def stop(self):
        self.is_running = False
        self.state = "IDLE"
        if config.hardware:
            config.hardware.release_all()
        print("[Logic] 사냥 중지")

    def pause(self):
        self.is_paused = True
        self.state = "PAUSED"

    def resume(self):
        self.is_paused = False
        self.state = "HUNTING"

    def step(self):
        if not self.is_running or self.is_paused: return

        # 1. 룬 체크
        if self.rune_manager.check_and_activate():
            self.state = "RUNE_SOLVING"
            self.rune_manager.step()
            return

        # 2. 일반 사냥
        self.state = "HUNTING"
        self.machine.step()
        
        # 3. [신규] 루틴 리필 로직
        # 현재 머신이 할 일을 다 끝냈는데(명령어 소진), 스케줄러가 있다면?
        if self.scheduler and self.machine.current_idx >= len(self.machine.commands):
            print("[Logic] 현재 사이클 종료. 다음 스케줄 생성 중...")
            
            # 다음 할 일 받아오기 (쿨타임 체크 -> 사냥 생성)
            next_routine = self.scheduler.get_next_routine()
            self.machine.set_routine(next_routine)
            
            # 머신 리셋 (다시 0번부터 실행)
            self.machine.current_idx = 0

    # GUI 호환성
    @property
    def current_logic(self): return self
    @property
    def summon_index(self): return 0
    @property
    def summon_points(self): return []
    @property
    def current_portal_idx(self): return 0
    @property
    def portal_points(self): return []