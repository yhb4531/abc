import time
import random
import core.config as config  # [중요] Config를 통해 전역 직업 설정 접근

class RoutineScheduler:
    def __init__(self, points, settings):
        self.points = points
        self.settings = settings
        
        self.last_used = {} 
        for i, p in enumerate(points):
            self.last_used[i] = -9999.0

        self.hunting_type = settings.get("hunting_type", "stationary")
        
        # [변경점] settings가 아니라 현재 로드된 Job 정보에서 키 가져오기
        self.attack_key = "attack" # 기본값
        self.sub_key = None        # 기본값 없음
        
        if config.job_manager and config.job_manager.job_data:
            keys = config.job_manager.job_data.get("keys", {})
            
            # 1. attack 키 확인 (없으면 그냥 attack)
            if "attack" in keys:
                self.attack_key = "attack"
                
            # 2. sub_attack 또는 sub 키 확인 (있으면 자동 할당)
            if "sub_attack" in keys:
                self.sub_key = "sub_attack"
            elif "sub" in keys:
                self.sub_key = "sub"
            
            print(f"[Scheduler] 키 설정 자동 감지 -> 주공격: {self.attack_key}, 보조: {self.sub_key}")

    def get_next_routine(self):
        routine = []
        now = time.time()
        
        # ... (이 부분은 이전과 100% 동일: 쿨타임 체크 로직) ...
        # (중복을 피하기 위해 생략하지 않고 핵심만 유지)
        
        next_expiry_time = float('inf') 
        safe_spot = None
        if self.points:
            safe_spot = self.points[-1]

        for i, p in enumerate(self.points):
            if i == len(self.points) - 1: continue

            cooldown = float(p.get("cooldown", 0))
            elapsed = now - self.last_used[i]
            
            if elapsed >= cooldown:
                routine.append({
                    "type": "move", 
                    "args": {"x": p["x"], "tolerance": 5}
                })
                
                pt_type = p.get("type")
                key = p.get("key")
                
                if pt_type in ["summon", "portal"] and key:
                    routine.append({"type": "key", "args": {"key_name": key, "duration": 0.2}})
                    routine.append({"type": "wait", "args": {"duration": 0.6}})
                
                self.last_used[i] = now
                expiry = now + cooldown
            else:
                expiry = self.last_used[i] + cooldown
            
            if expiry < next_expiry_time:
                next_expiry_time = expiry

        if safe_spot:
            routine.append({
                "type": "move", 
                "args": {"x": safe_spot["x"], "tolerance": 5}
            })

        hunt_duration = next_expiry_time - time.time()
        if hunt_duration < 10: hunt_duration = 10
        if hunt_duration > 180: hunt_duration = 60

        print(f"[Scheduler] 사냥 지속: {hunt_duration:.1f}초")
        routine.extend(self._create_hunt_routine(hunt_duration))

        return routine

    def _create_hunt_routine(self, duration):
        routine = []
        
        if self.hunting_type == "stationary":
            # [제자리 사냥]
            remaining = duration
            while remaining > 0:
                if remaining > 30:
                    chunk = random.uniform(15.0, 25.0)
                else:
                    chunk = remaining
                
                routine.append({
                    "type": "key",
                    "args": {"key_name": self.attack_key, "duration": chunk}
                })
                
                routine.append({"type": "wait", "args": {"duration": random.uniform(0.1, 0.3)}})
                
                # 보조키가 있을 때만 20% 확률로 사용
                if self.sub_key and random.random() < 0.2:
                    routine.append({
                        "type": "key", 
                        "args": {"key_name": self.sub_key, "duration": 0.15}
                    })
                    routine.append({"type": "wait", "args": {"duration": 0.3}})

                remaining -= chunk

        elif self.hunting_type == "portal":
            # [포탈 사냥]
            elapsed = 0
            while elapsed < duration:
                atk_time = random.uniform(2.1, 2.6)
                
                routine.append({
                    "type": "key",
                    "args": {"key_name": self.attack_key, "duration": atk_time}
                })
                
                routine.append({"type": "key", "args": {"key_name": "up", "duration": 0.15}})
                routine.append({"type": "wait", "args": {"duration": 0.1}})
                
                elapsed += (atk_time + 0.3)

        return routine