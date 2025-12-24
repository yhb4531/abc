from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QGroupBox, QRadioButton, QLineEdit, QFormLayout,
    QListWidget, QMessageBox
)
from PyQt5.QtCore import Qt
import cv2
import json
import os
import sys
import core.config as config

class MapTab(QWidget):
    def __init__(self):
        super().__init__()
        self.temp_points = []
        self.info_text = "준비됨"
        
        # 파일 경로 설정
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.maps_file = os.path.join(self.base_dir, "data", "maps.json")

        layout = QVBoxLayout() 

        # === [1] 맵 관리 ===
        manage_group = QGroupBox("저장된 맵 관리")
        manage_layout = QHBoxLayout()
        self.combo_saved_maps = QComboBox()
        self.combo_saved_maps.addItem("- 선택 -")
        self.combo_saved_maps.currentIndexChanged.connect(self.load_map_to_ui) 
        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self.refresh_map_list)
        btn_delete = QPushButton("삭제")
        btn_delete.setStyleSheet("background-color: #ffcdd2; color: #c62828; font-weight: bold;")
        btn_delete.clicked.connect(self.delete_map)
        manage_layout.addWidget(self.combo_saved_maps, stretch=1)
        manage_layout.addWidget(btn_refresh)
        manage_layout.addWidget(btn_delete)
        manage_group.setLayout(manage_layout)
        layout.addWidget(manage_group)

        # === [2] 설정 (가로 배치) ===
        middle_layout = QHBoxLayout()
        
        # 이름 및 저장
        name_group = QGroupBox("맵 설정")
        name_layout = QVBoxLayout()
        self.edit_map_name = QLineEdit()
        self.edit_map_name.setPlaceholderText("맵 이름 (예: Ludi_Mechanic)")
        btn_save = QPushButton("현재 상태 저장")
        btn_save.setStyleSheet("background-color: #c8e6c9; color: #2e7d32; font-weight: bold;")
        btn_save.clicked.connect(self.save_map)
        name_layout.addWidget(self.edit_map_name)
        name_layout.addWidget(btn_save)
        name_group.setLayout(name_layout)
        middle_layout.addWidget(name_group, stretch=1)

        # 사냥 방식
        type_group = QGroupBox("전체 사냥 방식")
        type_layout = QVBoxLayout()
        self.radio_stationary = QRadioButton("제자리 (난수 꾹 누르기)")
        self.radio_portal = QRadioButton("포탈 (공격 2초↑ + 윗키)")
        self.radio_stationary.setChecked(True) 
        type_layout.addWidget(self.radio_stationary)
        type_layout.addWidget(self.radio_portal)
        type_group.setLayout(type_layout)
        middle_layout.addWidget(type_group, stretch=1)
        layout.addLayout(middle_layout)

        # === [3] 포인트 설정 (하단) ===
        bottom_layout = QHBoxLayout()

        # 점 추가 설정
        pt_group = QGroupBox("점 추가 설정 (설정 후 미니맵 클릭)")
        pt_layout = QFormLayout()
        self.combo_pt_type = QComboBox()
        self.combo_pt_type.addItems(["summon (설치기)", "portal (포탈설치)", "move (단순이동)", "safe_spot (대기장소)"])
        
        self.edit_pt_key = QLineEdit()
        self.edit_pt_key.setPlaceholderText("키 이름 (예: q)")
        
        self.edit_pt_cool = QLineEdit("60") 
        self.edit_pt_cool.setPlaceholderText("초 (재설치 주기)")

        pt_layout.addRow("타입:", self.combo_pt_type)
        pt_layout.addRow("사용할 키:", self.edit_pt_key)
        pt_layout.addRow("쿨타임(초):", self.edit_pt_cool)
        pt_group.setLayout(pt_layout)
        bottom_layout.addWidget(pt_group) # stretch 제거하여 꽉 차게

        layout.addLayout(bottom_layout)

        # === [4] 좌표 목록 ===
        list_layout = QVBoxLayout()
        header = QHBoxLayout()
        header.addStretch()
        btn_clear = QPushButton("좌표 초기화")
        btn_clear.clicked.connect(self.clear_points)
        header.addWidget(btn_clear)
        list_layout.addLayout(header)
        self.list_points = QListWidget()
        list_layout.addWidget(self.list_points)
        layout.addLayout(list_layout)

        self.setLayout(layout)
        self.refresh_map_list()

    def handle_click(self, x, y):
        raw_type = self.combo_pt_type.currentText()
        pt_type = raw_type.split()[0]
        key = self.edit_pt_key.text().strip()
        cool = self.edit_pt_cool.text().strip()
        if not cool.isdigit(): cool = "0"

        point = {
            "x": x, "y": y, 
            "type": pt_type, 
            "key": key, 
            "cooldown": int(cool)
        }
        self.temp_points.append(point)
        
        display_text = f"[{pt_type}] ({x}, {y})"
        if key: display_text += f" Key:{key}"
        if int(cool) > 0: display_text += f" Cool:{cool}s"
        
        self.list_points.addItem(display_text)

    def save_map(self):
        name = self.edit_map_name.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "맵 이름을 입력해주세요.")
            return
        if not self.temp_points:
            QMessageBox.warning(self, "경고", "좌표가 없습니다.")
            return

        hunting_type = "stationary" if self.radio_stationary.isChecked() else "portal"
        
        # [변경점] 공격키/보조키 설정 제거 (자동 감지이므로 저장 안 함)
        settings = {
            "hunting_type": hunting_type
        }

        map_data = {
            "points": self.temp_points,
            "settings": settings
        }

        try:
            data = self.get_json_data()
            data[name] = map_data
            self.save_json_data(data)
            self.refresh_map_list()
            QMessageBox.information(self, "성공", f"맵 '{name}' 저장 완료!")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")

    # ... (나머지 get_json_data, save_json_data, refresh_map_list, delete_map, clear_points, draw_overlay 동일) ...
    # 전체 복사 시 아래 코드 포함해주세요.
    
    def get_json_data(self):
        if os.path.exists(self.maps_file):
            try:
                with open(self.maps_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}

    def save_json_data(self, data):
        with open(self.maps_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def refresh_map_list(self):
        self.combo_saved_maps.blockSignals(True)
        self.combo_saved_maps.clear()
        self.combo_saved_maps.addItem("- 선택 -")
        data = self.get_json_data()
        for name in data.keys():
            self.combo_saved_maps.addItem(name)
        self.combo_saved_maps.blockSignals(False)

    def load_map_to_ui(self):
        name = self.combo_saved_maps.currentText()
        if name == "- 선택 -": return
        data = self.get_json_data()
        map_data = data.get(name, {})
        
        self.edit_map_name.setText(name)
        settings = map_data.get("settings", {})
        
        h_type = settings.get("hunting_type", "stationary")
        if h_type == "portal": self.radio_portal.setChecked(True)
        else: self.radio_stationary.setChecked(True)

        self.temp_points = map_data.get("points", [])
        self.list_points.clear()
        for p in self.temp_points:
            pt_type = p.get('type', 'move')
            key = p.get('key', '')
            cool = str(p.get('cooldown', 0))
            x, y = p.get('x', 0), p.get('y', 0)
            
            display = f"[{pt_type}] ({x}, {y})"
            if key: display += f" Key:{key}"
            if cool != "0": display += f" Cool:{cool}s"
            self.list_points.addItem(display)

    def delete_map(self):
        name = self.combo_saved_maps.currentText()
        if name == "- 선택 -": return
        confirm = QMessageBox.question(self, "삭제 확인", f"'{name}' 삭제?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            data = self.get_json_data()
            if name in data:
                del data[name]
                self.save_json_data(data)
                self.refresh_map_list()
                self.clear_points()
                self.edit_map_name.clear()

    def clear_points(self):
        self.temp_points = []
        self.list_points.clear()

    def draw_overlay(self, img):
        for i, p in enumerate(self.temp_points):
            x, y = p['x'], p['y']
            pt_type = p['type']
            color = (0, 255, 0)
            if pt_type == 'summon': color = (0, 255, 255)
            elif pt_type == 'portal': color = (255, 0, 255)
            elif pt_type == 'safe_spot': color = (255, 0, 0)
            cv2.circle(img, (x, y), 5, color, -1)
            cv2.putText(img, str(i+1), (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            if i > 0:
                prev = self.temp_points[i-1]
                cv2.line(img, (prev['x'], prev['y']), (x, y), (200, 200, 200), 1)