from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QMessageBox, QRadioButton, QButtonGroup, QGroupBox
)
import cv2
import json
import time
import os
import sys # [필수]

class MapTab(QWidget):
    def __init__(self):
        super().__init__()
        self.vision = None 
        self.current_path = []
        self.info_text = "준비됨"

        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        self.input_map_name = QLineEdit()
        self.input_map_name.setPlaceholderText("맵 이름 입력")
        top_layout.addWidget(self.input_map_name)
        self.btn_save = QPushButton("저장")
        self.btn_save.clicked.connect(self.save_map_data)
        top_layout.addWidget(self.btn_save)
        layout.addLayout(top_layout)
        
        type_group = QGroupBox("포인트 타입")
        type_layout = QHBoxLayout()
        self.radio_move = QRadioButton("이동")
        self.radio_summon = QRadioButton("설치기")
        self.radio_portal = QRadioButton("포탈")
        self.radio_safe = QRadioButton("세이프")
        self.radio_move.setChecked(True)
        self.bg_type = QButtonGroup(self)
        self.bg_type.addButton(self.radio_move)
        self.bg_type.addButton(self.radio_summon)
        self.bg_type.addButton(self.radio_portal)
        self.bg_type.addButton(self.radio_safe)
        type_layout.addWidget(self.radio_move)
        type_layout.addWidget(self.radio_summon)
        type_layout.addWidget(self.radio_portal)
        type_layout.addWidget(self.radio_safe)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        dir_group = QGroupBox("방향 (세이프 스팟용)")
        dir_layout = QHBoxLayout()
        self.radio_left = QRadioButton("왼쪽")
        self.radio_right = QRadioButton("오른쪽")
        self.radio_left.setChecked(True)
        self.bg_dir = QButtonGroup(self)
        self.bg_dir.addButton(self.radio_left)
        self.bg_dir.addButton(self.radio_right)
        dir_layout.addWidget(self.radio_left)
        dir_layout.addWidget(self.radio_right)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        ctrl_layout = QHBoxLayout()
        self.btn_record = QPushButton("녹화 시작")
        self.btn_record.clicked.connect(self.toggle_recording)
        self.is_recording = False
        ctrl_layout.addWidget(self.btn_record)
        self.btn_undo = QPushButton("되돌리기")
        self.btn_undo.clicked.connect(self.undo_point)
        ctrl_layout.addWidget(self.btn_undo)
        self.btn_clear = QPushButton("초기화")
        self.btn_clear.clicked.connect(self.clear_path)
        ctrl_layout.addWidget(self.btn_clear)
        layout.addLayout(ctrl_layout)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_vision(self, vision_object):
        self.vision = vision_object

    def toggle_recording(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.btn_record.setText("녹화 중지")
            self.btn_record.setStyleSheet("background-color: #F44336; color: white;")
            self.info_text = "녹화 중... 상단 미니맵을 클릭하세요."
        else:
            self.btn_record.setText("녹화 시작")
            self.btn_record.setStyleSheet("")
            self.info_text = "녹화 중지됨."

    def handle_click(self, x, y):
        if not self.is_recording: return
        pt_type = 'move'
        if self.radio_summon.isChecked(): pt_type = 'summon'
        elif self.radio_portal.isChecked(): pt_type = 'portal'
        elif self.radio_safe.isChecked(): pt_type = 'safe_spot'
        new_point = {'x': x, 'y': y, 'type': pt_type}
        if pt_type == 'safe_spot':
            new_point['direction'] = 'left' if self.radio_left.isChecked() else 'right'
        self.current_path.append(new_point)
        self.info_text = f"[{pt_type}] 추가됨 ({x}, {y})"

    def draw_overlay(self, img):
        if len(self.current_path) > 0:
            for i, point in enumerate(self.current_path):
                px, py = point['x'], point['y']
                pt_type = point['type']
                color = (0, 255, 255)
                if pt_type == 'summon': color = (255, 0, 0)
                elif pt_type == 'portal': color = (255, 0, 255)
                elif pt_type == 'safe_spot': color = (0, 255, 0)
                cv2.circle(img, (px, py), 4, color, -1)
                if pt_type == 'safe_spot':
                    direction = point.get('direction', 'left')
                    offset = -10 if direction == 'left' else 10
                    cv2.line(img, (px, py), (px + offset, py), (0, 255, 0), 2)
                if i > 0:
                    prev = self.current_path[i-1]
                    cv2.line(img, (prev['x'], prev['y']), (px, py), (100, 100, 100), 1)

    def undo_point(self):
        if self.current_path: self.current_path.pop()

    def clear_path(self):
        self.current_path = []

    def get_maps_file_path(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            # tabs -> gui -> MaplePro (3번 올라감)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "data", "maps.json")

    def save_map_data(self):
        map_name = self.input_map_name.text().strip()
        if not map_name or not self.current_path:
            QMessageBox.warning(self, "경고", "이름/경로 확인")
            return
        
        file_path = self.get_maps_file_path()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        new_data = {"points": self.current_path, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        try: data = json.load(open(file_path, 'r', encoding='utf-8')) if os.path.exists(file_path) else {}
        except: data = {}
        data[map_name] = new_data
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "완료", f"저장됨: {map_name}\n경로: {file_path}")