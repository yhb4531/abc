import time
import random
import core.config as config  

class RoutineScheduler:
    def __init__(self, points, settings):
        self.points = points
        self.settings = settings
        
        self.last_used = {} 
        for i, p in enumerate(points):
            self.last_used[i] = -9999.0

        self.hunting_type = settings.get("hunting_type", "stationary")
        
        self.attack_key = "attack" 
        self.sub_key = None        
        
        # [수정된 부분] job_data -> current_job 으로 변경
        if config.job_manager and config.job_manager.current_job:
            keys = config.job_manager.current_job.get("keys", {})
            
            if "attack" in keys:
                self.attack_key = "attack"
                
            if "sub_attack" in keys:
                self.sub_key = "sub_attack"
            elif "sub" in keys:
                self.sub_key = "sub"
            
            print(f"[Scheduler] 키 설정 자동 감지 -> 주공격: {self.attack_key}, 보조: {self.sub_key}")

    def get_next_routine(self):
        routine = []
        now = time.time()
        
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
                    "args": {
                        "x": p["x"], 
                        "y": p.get("y"), # y좌표 안전하게 가져오기
                        "tolerance": 5
                    }
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
                "args": {
                    "x": safe_spot["x"], 
                    "y": safe_spot.get("y"), # y좌표
                    "tolerance": 5
                }
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
                
                if self.sub_key and random.random() < 0.2:
                    routine.append({
                        "type": "key", 
                        "args": {"key_name": self.sub_key, "duration": 0.15}
                    })
                    routine.append({"type": "wait", "args": {"duration": 0.3}})

                remaining -= chunk

        elif self.hunting_type == "portal":
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