from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
import cv2
import os
import json
import time
import sys
import core.config as config

# ==========================================
# 스레드 (로직 실행용)
# ==========================================
class HuntingThread(QThread):
    status_update = pyqtSignal(str) 

    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.running = True
        self.last_msg = ""

    def run(self):
        while self.running:
            if self.logic and self.logic.current_logic:
                self.logic.step()
                state_msg = self.get_state_message()
                if state_msg != self.last_msg:
                    self.status_update.emit(state_msg)
                    self.last_msg = state_msg
            time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()

    def get_state_message(self):
        if not self.logic.current_logic: return "로직 없음"
        core = self.logic.current_logic
        state = core.state
        
        if state == "SETUP":
            if hasattr(core, 'summon_index'):
                idx = core.summon_index + 1
                total = len(core.summon_points)
                return f"설치기 설치 중 ({idx}/{total})"
            return "설치 중"
        elif state == "INSTALL":
            idx = core.current_portal_idx + 1
            total = len(core.portal_points)
            return f"포탈 설치 중 ({idx}/{total})"
        elif state == "MOVING_TO_SAFE": return "안전지대 이동 중"
        elif state == "HUNTING":
            elapsed = time.time() - core.cycle_start_time
            remain = max(0, int(core.cycle_duration - elapsed))
            if core.is_paused: return f"일시정지됨 (재설치까지 {remain}s)" # 일시정지 상태 표시
            return f"제자리 사냥 중 (재설치까지 {remain}s)"
        elif state == "ATTACKING":
            elapsed = time.time() - core.cycle_start_time
            remain = max(0, int(core.cycle_duration - elapsed))
            if core.is_paused: return f"일시정지됨 (재설치까지 {remain}s)"
            return f"포탈 사냥 중 (재설치까지 {remain}s)"
        return state

# ==========================================
# 탭 클래스
# ==========================================
class HomeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.logic = None
        self.hunting_thread = None
        self.vision = None
        self.preview_points = []

        layout = QVBoxLayout()
        
        # 1. 사냥터 선택
        sel_group = QGroupBox("사냥터 선택")
        sel_layout = QHBoxLayout()
        self.combo_maps = QComboBox()
        self.combo_maps.currentIndexChanged.connect(self.on_map_selected)
        sel_layout.addWidget(self.combo_maps, stretch=1)
        
        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self.refresh_map_list)
        sel_layout.addWidget(btn_refresh)
        sel_group.setLayout(sel_layout)
        layout.addWidget(sel_group)

        # 2. 제어 패널
        ctrl_group = QGroupBox("제어 패널")
        ctrl_layout = QVBoxLayout()
        
        self.btn_lock = QPushButton("미니맵 위치 고정 (Lock)")
        self.btn_lock.setCheckable(True)
        self.btn_lock.setFixedHeight(40)
        self.btn_lock.setStyleSheet("background-color: #555; color: white; font-weight: bold;")
        self.btn_lock.clicked.connect(self.toggle_minimap_lock)
        ctrl_layout.addWidget(self.btn_lock)

        self.lbl_detail = QLabel("대기 중...")
        self.lbl_detail.setAlignment(Qt.AlignCenter)
        self.lbl_detail.setStyleSheet("font-size: 14px; margin: 10px 0;")
        ctrl_layout.addWidget(self.lbl_detail)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("시작")
        self.btn_start.setFixedHeight(50)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px;")
        self.btn_start.clicked.connect(self.toggle_start)
        
        # [일시정지 버튼]
        self.btn_pause = QPushButton("일시정지")
        self.btn_pause.setFixedHeight(50)
        self.btn_pause.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; font-size: 16px;")
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        
        self.btn_stop = QPushButton("정지")
        self.btn_stop.setFixedHeight(50)
        self.btn_stop.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; font-size: 16px;")
        self.btn_stop.clicked.connect(self.stop_hunting)
        self.btn_stop.setEnabled(False)
        
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        ctrl_layout.addLayout(btn_row)
        ctrl_group.setLayout(ctrl_layout)
        layout.addWidget(ctrl_group)
        
        layout.addStretch(1)
        self.setLayout(layout)
        
        self.refresh_map_list()

    def set_logic(self, logic_manager): self.logic = logic_manager
    def set_vision(self, vision): self.vision = vision

    def toggle_minimap_lock(self):
        if not self.vision: return
        is_locked = self.btn_lock.isChecked()
        self.vision.is_minimap_locked = is_locked
        if is_locked:
            self.btn_lock.setText("위치 고정됨 (Unlock)")
            self.btn_lock.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold;")
        else:
            self.btn_lock.setText("미니맵 위치 고정 (Lock)")
            self.btn_lock.setStyleSheet("background-color: #555; color: white; font-weight: bold;")

    # 일시정지 토글
    def toggle_pause(self):
        if not self.logic or not self.logic.is_running: return
        
        if self.logic.is_paused:
            self.logic.resume()
            self.btn_pause.setText("일시정지")
            self.btn_pause.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; font-size: 16px;")
        else:
            self.logic.pause()
            self.btn_pause.setText("재개")
            self.btn_pause.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; font-size: 16px;")

    def get_maps_file_path(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "data", "maps.json")

    def refresh_map_list(self):
        self.combo_maps.clear()
        try:
            file_path = self.get_maps_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.combo_maps.addItems(list(data.keys()))
        except: pass
        self.on_map_selected()

    def on_map_selected(self):
        map_name = self.combo_maps.currentText()
        self.preview_points = []
        if not map_name: return
        try:
            file_path = self.get_maps_file_path()
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.preview_points = data.get(map_name, {}).get("points", [])
        except: self.preview_points = []

    def draw_overlay(self, img):
        if self.preview_points:
            for i, p in enumerate(self.preview_points):
                if isinstance(p, dict):
                    px, py = p['x'], p['y']
                    pt_type = p.get('type', 'move')
                else: continue
                color = (0, 255, 255)
                if pt_type == 'summon': color = (255, 0, 0)
                elif pt_type == 'portal': color = (255, 0, 255)
                elif pt_type == 'safe_spot': color = (0, 255, 0)
                cv2.circle(img, (px, py), 4, color, -1)
                if i > 0:
                    prev = self.preview_points[i-1]
                    if isinstance(prev, dict):
                        cv2.line(img, (prev['x'], prev['y']), (px, py), (100, 100, 100), 1)

    # [중요] 지난번에 누락되었던 함수 포함됨!
    def update_status_label(self, msg):
        self.lbl_detail.setText(msg)

    def start_hunting(self):
        if not self.logic: return
        map_name = self.combo_maps.currentText()
        if not map_name:
            QMessageBox.warning(self, "오류", "선택된 맵이 없습니다.")
            return
        if not self.logic.load_path(map_name):
            QMessageBox.critical(self, "오류", "경로 로드 실패")
            return
        
        self.logic.start()
        self.hunting_thread = HuntingThread(self.logic)
        self.hunting_thread.status_update.connect(self.update_status_label)
        self.hunting_thread.start()
        
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True) # 일시정지 활성화
        self.btn_stop.setEnabled(True)
        self.lbl_detail.setText("가동 준비 중...")

    def stop_hunting(self):
        if self.hunting_thread:
            self.hunting_thread.stop()
            self.hunting_thread = None
        if self.logic:
            self.logic.stop()
        
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setText("일시정지")
        self.lbl_detail.setText("중지됨")
    
    # 기존 함수들 아래에 추가하세요
    @pyqtSlot()
    def toggle_start(self):
        import core.config as config

        if not self.logic: return

        # === [1] 봇이 켜져 있으면 -> 끄기 ===
        if config.enabled:
            if self.hunting_thread:
                self.hunting_thread.stop()
                self.hunting_thread = None
            if self.logic:
                self.logic.stop()
            
            config.enabled = False
            
            self.btn_start.setText("시작")
            self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px;")
            self.btn_pause.setEnabled(False)
            self.lbl_detail.setText("중지됨")
        
        # === [2] 봇이 꺼져 있으면 -> 켜기 ===
        else:
            # 1. 콤보박스에서 맵 이름 가져오기
            map_name = self.combo_maps.currentText()
            if not map_name:
                QMessageBox.warning(self, "오류", "선택된 맵이 없습니다.")
                return
            
            # 2. [핵심] 로직에 맵 데이터 로드하기 (이게 빠져서 오류가 났던 것)
            if not self.logic.load_path(map_name):
                QMessageBox.critical(self, "오류", f"'{map_name}' 경로 로드 실패")
                return
            
            # 3. 로직 시작
            self.logic.start()
            config.enabled = True
            
            # 4. 스레드 시작
            self.hunting_thread = HuntingThread(self.logic)
            self.hunting_thread.status_update.connect(self.update_status_label)
            self.hunting_thread.start()
            
            self.btn_start.setText("정지")
            self.btn_start.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; font-size: 16px;")
            self.btn_pause.setEnabled(True)
            self.lbl_detail.setText("가동 중...")