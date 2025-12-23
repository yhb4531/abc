import time
import random

class CombatSystem:
    def __init__(self, hardware, job_manager):
        self.hw = hardware
        self.job_manager = job_manager
        self.attack_key = self.job_manager.get_key("attack")
        self.jump_key = self.job_manager.get_key("jump")
        self.rope_key = self.job_manager.get_key("rope")
        
        # [추가] 보조 스킬 설정 로드
        self.aux_data = self.job_manager.get_aux_skill()
        self.aux_key = self.aux_data.get("key", None)
        self.aux_mode = self.aux_data.get("mode", None)

    def sleep_random(self, min_t, max_t):
        time.sleep(random.uniform(min_t, max_t))

    def hold_attack(self):
        # 1. 주력기 누름
        if self.attack_key:
            self.hw.hold(self.attack_key)
        
        # 2. [Sync 모드] 보조키도 같이 누름 (메카닉 호밍 등)
        if self.aux_key and self.aux_mode == "sync":
            # 동시에 누르는 느낌을 주기 위해 딜레이 없이 바로 명령
            self.hw.hold(self.aux_key)

    def release_attack(self):
        # 1. 주력기 뗌
        if self.attack_key:
            self.hw.release(self.attack_key)
            
        # 2. [Sync 모드] 보조키도 같이 뗌
        if self.aux_key and self.aux_mode == "sync":
            self.hw.release(self.aux_key)

    def use_summon_at_index(self, index):
        skills = self.job_manager.get_skills()
        summons = skills.get("summons", [])
        if index < len(summons):
            key = summons[index]
            press_duration = random.gauss(0.25, 0.02)
            self.hw.press(key, duration=press_duration)
            self.sleep_random(0.75, 0.9)

    def install_portal(self):
        skills = self.job_manager.get_skills()
        portal_key = skills.get("portal")
        if portal_key:
            self.hw.press(portal_key, duration=random.uniform(0.15, 0.25)) 
            self.sleep_random(0.75, 0.95)

    def use_upper_portal(self):
        """ 윗점프 포탈 """
        self.release_attack() # 여기서 보조키도 같이 떼짐
        
        hold_duration = random.uniform(0.45, 0.58)
        self.hw.hold('up')
        time.sleep(hold_duration) 
        self.hw.release('up')
        
        self.sleep_random(0.02, 0.06)
        self.hold_attack() # 여기서 보조키도 같이 눌림