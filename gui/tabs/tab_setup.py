from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QGroupBox, QRadioButton, QFormLayout, 
    QMessageBox, QButtonGroup 
)
from PyQt5.QtCore import Qt
import sys
import os

class SetupTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.job_manager = None
        self.hardware = None # MainWindow에서 받을 예정
        self.layout = QVBoxLayout()
        
        # === [유지] 하드웨어 수동 연결 패널 ===
        hw_group = QGroupBox("하드웨어 연결 (수동)")
        hw_layout = QHBoxLayout()
        
        self.input_port = QLineEdit()
        self.input_port.setPlaceholderText("예: COM3")
        hw_layout.addWidget(QLabel("포트:"))
        hw_layout.addWidget(self.input_port)
        
        self.btn_connect = QPushButton("피코 연결하기")
        self.btn_connect.clicked.connect(self.connect_hardware)
        self.btn_connect.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        hw_layout.addWidget(self.btn_connect)
        
        hw_group.setLayout(hw_layout)
        self.layout.addWidget(hw_group)
        # ========================================
        
        # 1. 직업 선택
        job_select_layout = QHBoxLayout()
        job_select_layout.addWidget(QLabel("직업 선택 (직접 입력 가능):"))
        self.combo_jobs = QComboBox()
        self.combo_jobs.setEditable(True) 
        self.combo_jobs.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.combo_jobs.currentIndexChanged.connect(self.load_job_to_ui)
        job_select_layout.addWidget(self.combo_jobs)
        self.layout.addLayout(job_select_layout)
        
        # 2. 이동 방식
        self.group_move = QGroupBox("이동 방식")
        move_layout = QVBoxLayout()
        type_layout = QHBoxLayout()
        self.radio_flash = QRadioButton("플래시 점프")
        self.radio_tele = QRadioButton("텔레포트")
        self.bg_move_type = QButtonGroup(self)
        self.bg_move_type.addButton(self.radio_flash)
        self.bg_move_type.addButton(self.radio_tele)
        type_layout.addWidget(self.radio_flash)
        type_layout.addWidget(self.radio_tele)
        move_layout.addLayout(type_layout)
        
        up_layout = QHBoxLayout()
        up_layout.addWidget(QLabel("윗점프:"))
        self.radio_up_cmd = QRadioButton("커맨드 (↑+점프)")
        self.radio_up_key = QRadioButton("전용 키")
        self.bg_up_jump = QButtonGroup(self)
        self.bg_up_jump.addButton(self.radio_up_cmd)
        self.bg_up_jump.addButton(self.radio_up_key)
        up_layout.addWidget(self.radio_up_cmd)
        up_layout.addWidget(self.radio_up_key)
        move_layout.addLayout(up_layout)
        self.group_move.setLayout(move_layout)
        self.layout.addWidget(self.group_move)
        
        # 3. 키 세팅
        self.group_keys = QGroupBox("키 설정")
        form_layout = QFormLayout()
        self.input_jump = QLineEdit()
        self.input_teleport = QLineEdit()
        self.input_attack = QLineEdit()
        self.input_interact = QLineEdit()
        self.input_rope = QLineEdit()
        
        # [변경됨] 펫 먹이 -> 보조 스킬
        self.input_aux = QLineEdit() 
        
        form_layout.addRow("점프:", self.input_jump)
        form_layout.addRow("텔레포트:", self.input_teleport)
        form_layout.addRow("주력기:", self.input_attack)
        form_layout.addRow("채집/룬:", self.input_interact)
        form_layout.addRow("로프:", self.input_rope)
        
        # [변경됨] 라벨 수정
        form_layout.addRow("보조 스킬 (Sync):", self.input_aux)
        
        self.group_keys.setLayout(form_layout)
        self.layout.addWidget(self.group_keys)
        
        # 4. 스킬 키
        self.group_skills = QGroupBox("스킬 설정")
        skill_layout = QFormLayout()
        self.input_summons = QLineEdit()
        self.input_summons.setPlaceholderText("예: e, 4")
        self.input_portal = QLineEdit()
        skill_layout.addRow("설치기:", self.input_summons)
        skill_layout.addRow("포탈:", self.input_portal)
        self.group_skills.setLayout(skill_layout)
        self.layout.addWidget(self.group_skills)
        
        # 5. 저장 버튼
        self.btn_save = QPushButton("설정 저장")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_settings)
        self.layout.addWidget(self.btn_save)
        
        self.layout.addStretch(1)
        self.setLayout(self.layout)

    def set_job_manager(self, job_manager):
        self.job_manager = job_manager
        self.combo_jobs.blockSignals(True)
        self.combo_jobs.clear()
        self.combo_jobs.addItems(self.job_manager.get_all_job_names())
        current_idx = self.combo_jobs.findText(self.job_manager.active_job_name)
        if current_idx >= 0: self.combo_jobs.setCurrentIndex(current_idx)
        self.combo_jobs.blockSignals(False)
        self.load_job_to_ui()

    def set_hardware(self, hardware):
        self.hardware = hardware

    def connect_hardware(self):
        if not self.hardware: return
        
        port = self.input_port.text().strip()
        if not port:
            QMessageBox.warning(self, "경고", "포트 번호를 입력하세요 (예: COM6)")
            return
            
        self.btn_connect.setText("연결 시도 중...")
        self.btn_connect.setEnabled(False)
        QMessageBox.information(self, "알림", "연결을 시도합니다. 잠시만 기다려주세요.\n(창이 멈춰도 5초만 기다리세요)")
        
        if self.hardware.find_and_connect(port):
            QMessageBox.information(self, "성공", f"✅ {port} 연결 성공!")
            self.btn_connect.setText("연결됨")
            self.btn_connect.setStyleSheet("background-color: green; color: white;")
        else:
            QMessageBox.critical(self, "실패", f"❌ {port} 연결 실패.\n다른 포트를 입력해보세요.")
            self.btn_connect.setText("피코 연결하기")
            self.btn_connect.setEnabled(True)
            self.btn_connect.setStyleSheet("background-color: #FF9800; color: white;")

    def load_job_to_ui(self):
        if not self.job_manager: return
        job_name = self.combo_jobs.currentText()
        job_data = self.job_manager.jobs_data["jobs"].get(job_name, {})
        if not job_data: return
        
        if self.job_manager.active_job_name != job_name:
            self.job_manager.set_active_job(job_name)
            
        keys = job_data.get("keys", {})
        self.input_jump.setText(keys.get("jump", ""))
        self.input_teleport.setText(keys.get("teleport", ""))
        self.input_attack.setText(keys.get("attack", ""))
        self.input_interact.setText(keys.get("interact", ""))
        self.input_rope.setText(keys.get("rope", ""))
        
        # [변경됨] 펫 먹이 대신 aux_skill 로드
        aux_data = job_data.get("aux_skill", {})
        self.input_aux.setText(aux_data.get("key", ""))
        
        movement = job_data.get("movement", {})
        if movement.get("type", "flash_jump") == "teleport": self.radio_tele.setChecked(True)
        else: self.radio_flash.setChecked(True)
        if movement.get("up_jump_method", "command") == "key": self.radio_up_key.setChecked(True)
        else: self.radio_up_cmd.setChecked(True)
        
        skills = job_data.get("skills", {})
        summons = skills.get("summons", [])
        self.input_summons.setText(", ".join(summons))
        self.input_portal.setText(skills.get("portal", ""))

    def save_settings(self):
        if not self.job_manager: return
        job_name = self.combo_jobs.currentText().strip()
        if not job_name:
            QMessageBox.warning(self, "경고", "직업 이름을 입력하세요.")
            return
            
        new_keys = {
            "jump": self.input_jump.text().strip(),
            "teleport": self.input_teleport.text().strip(),
            "attack": self.input_attack.text().strip(),
            "interact": self.input_interact.text().strip(),
            "rope": self.input_rope.text().strip(),
            # [변경됨] pet_food 제거
        }
        
        mv_type = "teleport" if self.radio_tele.isChecked() else "flash_jump"
        up_method = "key" if self.radio_up_key.isChecked() else "command"
        
        summ_text = self.input_summons.text()
        summons_list = [k.strip() for k in summ_text.split(",") if k.strip()]
        new_skills = {"summons": summons_list, "portal": self.input_portal.text().strip()}
        
        # [추가됨] 보조 스킬 (Sync) 저장 로직
        new_aux = {}
        aux_key_val = self.input_aux.text().strip()
        if aux_key_val:
            new_aux = {
                "key": aux_key_val,
                "mode": "sync"
            }
        
        new_settings = {
            "keys": new_keys,
            "movement": { "type": mv_type, "up_jump_method": up_method },
            "skills": new_skills,
            "aux_skill": new_aux # 저장 구조에 추가
        }
        
        self.job_manager.update_job_settings(job_name, new_settings)
        self.job_manager.set_active_job(job_name)
        if self.combo_jobs.findText(job_name) == -1: self.combo_jobs.addItem(job_name)
        QMessageBox.information(self, "저장 완료", f"'{job_name}' 설정이 저장되었습니다.")