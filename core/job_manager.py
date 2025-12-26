import json
import os
import sys

class JobManager:
    def __init__(self):
        # 경로 설정
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.file_path = os.path.join(base_dir, "data", "jobs.json")
        
        self.jobs_data = self.load_jobs()
        self.reload_current_job()

    def load_jobs(self):
        """ 파일 전체를 읽어오는 함수 """
        try:
            if not os.path.exists(self.file_path):
                return {"active_job": "Default", "jobs": {}}
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[JobManager] 로드 실패: {e}")
            return {"active_job": "Default", "jobs": {}}

    def load_job(self, job_name):
        """ 특정 직업 하나만 활성화하고 다시 읽는 함수 (GUI 호출용) """
        self.jobs_data = self.load_jobs()
        
        if job_name in self.jobs_data.get("jobs", {}):
            self.jobs_data["active_job"] = job_name
            self.reload_current_job()
            self.save_jobs()
            print(f"[JobManager] 직업 로드 완료: {job_name}")

    def save_jobs(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.jobs_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[JobManager] 저장 실패: {e}")
            return False

    def reload_current_job(self):
        self.active_job_name = self.jobs_data.get("active_job", "")
        self.current_job = self.jobs_data.get("jobs", {}).get(self.active_job_name, {})

    def set_active_job(self, job_name):
        if "jobs" in self.jobs_data and job_name in self.jobs_data["jobs"]:
            self.jobs_data["active_job"] = job_name
            self.reload_current_job()
            self.save_jobs()

    def get_all_job_names(self): 
        return list(self.jobs_data.get("jobs", {}).keys())
    
    # === 키 관련 함수 ===
    def get_key(self, action_name): 
        return self.current_job.get("keys", {}).get(action_name)
    
    # === 이동 관련 함수 ===
    def get_movement_type(self): 
        # 신규: move_mode / 구형: movement.type 호환
        mode = self.current_job.get("move_mode")
        if not mode:
            mode = self.current_job.get("movement", {}).get("type", "flash_jump")
        return mode

    # [복구됨] Navigator 호환성용 윗점프 메소드
    def get_up_jump_method(self):
        # 우리는 이제 로직에서 키 여부로 판단하므로, Navigator에게는 기본값 "command"를 줍니다.
        # 구형 데이터 호환
        method = self.current_job.get("movement", {}).get("up_jump_method", "command")
        return method

    # === 스킬 관련 함수 ===
    def get_skills(self): 
        return self.current_job.get("skills", {})
    
    # [복구됨] 혹시 모를 호환성용
    def get_aux_skill(self):
        return self.current_job.get("aux_skill", {})