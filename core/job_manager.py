import json
import os
import sys

class JobManager:
    def __init__(self):
        # [경로 로직]
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.file_path = os.path.join(base_dir, "data", "jobs.json")
        
        self.jobs_data = self.load_jobs()
        self.reload_current_job()

    def load_jobs(self):
        try:
            if not os.path.exists(self.file_path):
                return {"active_job": "Default", "jobs": {}}
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[JobManager] 로드 실패: {e}")
            return {"active_job": "Default", "jobs": {}}

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
        if job_name in self.jobs_data["jobs"]:
            self.jobs_data["active_job"] = job_name
            self.reload_current_job()
            self.save_jobs()

    def update_job_settings(self, job_name, new_settings):
        if "jobs" not in self.jobs_data:
            self.jobs_data["jobs"] = {}
        self.jobs_data["jobs"][job_name] = new_settings
        self.reload_current_job()
        self.save_jobs()

    def get_all_job_names(self): return list(self.jobs_data.get("jobs", {}).keys())
    def get_key(self, action_name): return self.current_job.get("keys", {}).get(action_name)
    def get_movement_type(self): return self.current_job.get("movement", {}).get("type", "flash_jump")
    def get_up_jump_method(self): return self.current_job.get("movement", {}).get("up_jump_method", "command")
    def get_skills(self): return self.current_job.get("skills", {})
    
    # [추가됨] 보조 스킬 정보 가져오기
    def get_aux_skill(self):
        return self.current_job.get("aux_skill", {})