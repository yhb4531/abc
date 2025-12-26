from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFormLayout, QComboBox, QGroupBox, QMessageBox,
    QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt
import json
import os
import sys
import serial.tools.list_ports # 포트 검색용
import core.config as config

class SetupTab(QWidget):
    def __init__(self):
        super().__init__()
        
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.jobs_file = os.path.join(self.base_dir, "data", "jobs.json")

        self.job_manager = None
        self.hardware = None

        self.layout = QVBoxLayout()

        # === [0] 하드웨어(Pico) 연결 섹션 (복구됨!) ===
        hw_group = QGroupBox("하드웨어 연결 (Raspberry Pi Pico)")
        hw_layout = QHBoxLayout()
        
        self.combo_ports = QComboBox()
        self.btn_refresh = QPushButton("포트 새로고침")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        
        self.btn_connect = QPushButton("연결")
        self.btn_connect.setStyleSheet("background-color: #ddd;") # 기본 회색
        self.btn_connect.clicked.connect(self.toggle_connect)
        
        hw_layout.addWidget(QLabel("COM 포트:"))
        hw_layout.addWidget(self.combo_ports, stretch=1)
        hw_layout.addWidget(self.btn_refresh)
        hw_layout.addWidget(self.btn_connect)
        hw_group.setLayout(hw_layout)
        self.layout.addWidget(hw_group)

        # === [1] 직업 관리 ===
        job_group = QGroupBox("직업 관리")
        job_layout = QHBoxLayout()
        self.combo_jobs = QComboBox()
        self.combo_jobs.currentIndexChanged.connect(self.load_job_data)
        self.btn_add_job = QPushButton("새 직업 추가")
        self.btn_add_job.clicked.connect(self.add_new_job)
        self.btn_delete_job = QPushButton("삭제")
        self.btn_delete_job.setStyleSheet("color: red;")
        self.btn_delete_job.clicked.connect(self.delete_job)
        job_layout.addWidget(QLabel("직업 선택:"))
        job_layout.addWidget(self.combo_jobs, stretch=1)
        job_layout.addWidget(self.btn_add_job)
        job_layout.addWidget(self.btn_delete_job)
        job_group.setLayout(job_layout)
        self.layout.addWidget(job_group)

        # === [2] 이동 방식 ===
        move_group = QGroupBox("이동 방식 (Smart Movement용)")
        move_layout = QHBoxLayout()
        self.radio_flash = QRadioButton("플래시 점프 (Jump + Jump)")
        self.radio_tele = QRadioButton("텔레포트 (Dir + Teleport)")
        self.bg_move = QButtonGroup()
        self.bg_move.addButton(self.radio_flash)
        self.bg_move.addButton(self.radio_tele)
        move_layout.addWidget(self.radio_flash)
        move_layout.addWidget(self.radio_tele)
        move_group.setLayout(move_layout)
        self.layout.addWidget(move_group)

        # === [3] 필수 키 매핑 ===
        key_group = QGroupBox("필수 키 설정 (Jobs.json)")
        key_layout = QFormLayout()
        
        self.input_attack = QLineEdit()
        self.input_sub = QLineEdit()
        self.input_jump = QLineEdit()
        self.input_rope = QLineEdit()
        self.input_interact = QLineEdit()
        self.input_teleport = QLineEdit()
        
        self.input_attack.setPlaceholderText("예: ctrl, a")
        self.input_sub.setPlaceholderText("보조 스킬 (선택)")
        self.input_jump.setPlaceholderText("점프 키 (필수)")
        self.input_rope.setPlaceholderText("로프 커넥트 (선택)")
        self.input_interact.setPlaceholderText("채집/룬 키 (필수)")
        self.input_teleport.setPlaceholderText("텔포 직업만 설정")

        key_layout.addRow("주 공격 (attack):", self.input_attack)
        key_layout.addRow("보조 공격 (sub_attack):", self.input_sub)
        key_layout.addRow("점프 (jump):", self.input_jump)
        key_layout.addRow("로프 (rope):", self.input_rope)
        key_layout.addRow("채집/룬 (interact):", self.input_interact)
        key_layout.addRow("텔레포트 (teleport):", self.input_teleport)
        key_group.setLayout(key_layout)
        self.layout.addWidget(key_group)

        # === [4] 저장 버튼 ===
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("설정 저장 (Save)")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_job_data)
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

        self.setLayout(self.layout)
        
        self.refresh_ports()
        self.refresh_job_list()

    # === 하드웨어 관련 함수 ===
    def refresh_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.combo_ports.addItem(f"{p.device}") # ({p.description}) 제거하여 심플하게

    def toggle_connect(self):
        if not self.hardware: return

        if self.hardware.is_connected():
            self.hardware.disconnect()
            self.btn_connect.setText("연결")
            self.btn_connect.setStyleSheet("background-color: #ddd; color: black;")
            QMessageBox.information(self, "연결 해제", "하드웨어 연결이 해제되었습니다.")
        else:
            port = self.combo_ports.currentText().split()[0]
            if not port:
                QMessageBox.warning(self, "오류", "포트를 선택해주세요.")
                return
            
            if self.hardware.connect(port):
                self.btn_connect.setText("연결됨")
                self.btn_connect.setStyleSheet("background-color: #4CAF50; color: white;")
                QMessageBox.information(self, "성공", f"{port}에 연결되었습니다.")
            else:
                QMessageBox.critical(self, "실패", "연결에 실패했습니다.")

    def set_job_manager(self, job_manager):
        self.job_manager = job_manager

    def set_hardware(self, hardware):
        self.hardware = hardware
        # 이미 연결돼있는 경우 UI 반영
        if self.hardware and self.hardware.is_connected():
            self.btn_connect.setText("연결됨")
            self.btn_connect.setStyleSheet("background-color: #4CAF50; color: white;")

    # === 직업 관련 함수 (기존 유지) ===
    def get_jobs_data(self):
        if os.path.exists(self.jobs_file):
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_jobs_file(self, data):
        with open(self.jobs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def refresh_job_list(self):
        self.combo_jobs.blockSignals(True)
        self.combo_jobs.clear()
        data = self.get_jobs_data()
        if not data:
            data = {"Default": {"keys": {}, "move_mode": "flash_jump"}}
            self.save_jobs_file(data)
        for name in data.keys():
            if name != "active_job": self.combo_jobs.addItem(name)
        self.combo_jobs.blockSignals(False)
        self.load_job_data()

    def add_new_job(self):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, '새 직업', '직업 이름:')
        if ok and text:
            data = self.get_jobs_data()
            if text in data:
                QMessageBox.warning(self, "오류", "이미 존재합니다.")
                return
            data[text] = {"move_mode": "flash_jump", "keys": {"attack": "ctrl", "jump": "alt", "interact": "space"}}
            self.save_jobs_file(data)
            self.refresh_job_list()
            self.combo_jobs.setCurrentText(text)

    def delete_job(self):
        name = self.combo_jobs.currentText()
        if not name: return
        reply = QMessageBox.question(self, "삭제", f"'{name}' 삭제?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            data = self.get_jobs_data()
            if name in data:
                del data[name]
                self.save_jobs_file(data)
                self.refresh_job_list()

    def load_job_data(self):
        name = self.combo_jobs.currentText()
        if not name: return
        data = self.get_jobs_data()
        job_data = data.get(name, {})
        keys = job_data.get("keys", {})
        
        mode = job_data.get("move_mode", "flash_jump")
        if mode == "teleport": self.radio_tele.setChecked(True)
        else: self.radio_flash.setChecked(True)
            
        self.input_attack.setText(keys.get("attack", ""))
        self.input_sub.setText(keys.get("sub_attack", keys.get("sub", "")))
        self.input_jump.setText(keys.get("jump", ""))
        self.input_rope.setText(keys.get("rope", ""))
        self.input_interact.setText(keys.get("interact", ""))
        self.input_teleport.setText(keys.get("teleport", ""))

        if config.job_manager:
            config.job_manager.load_job(name)

    def save_job_data(self):
        name = self.combo_jobs.currentText()
        if not name: return
        move_mode = "teleport" if self.radio_tele.isChecked() else "flash_jump"
        keys = {}
        if self.input_attack.text(): keys["attack"] = self.input_attack.text().strip()
        if self.input_sub.text(): keys["sub_attack"] = self.input_sub.text().strip()
        if self.input_jump.text(): keys["jump"] = self.input_jump.text().strip()
        if self.input_rope.text(): keys["rope"] = self.input_rope.text().strip()
        if self.input_interact.text(): keys["interact"] = self.input_interact.text().strip()
        if self.input_teleport.text(): keys["teleport"] = self.input_teleport.text().strip()
        keys["left"] = "left"; keys["right"] = "right"; keys["up"] = "up"; keys["down"] = "down"

        data = self.get_jobs_data()
        data[name] = {"move_mode": move_mode, "keys": keys}
        self.save_jobs_file(data)
        
        if config.job_manager:
            config.job_manager.load_job(name)
        QMessageBox.information(self, "저장 완료", f"'{name}' 저장됨")