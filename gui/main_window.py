from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QTabWidget, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
import sys
import os
import cv2

# 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.tabs.tab_home import HomeTab
from gui.tabs.tab_map import MapTab
from gui.tabs.tab_setup import SetupTab
from core.navigation import Navigator
from core.job_manager import JobManager
from logic.hunting import HuntingManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realtek Audio Manager")
        
        self.resize(500, 750) 

        # 모듈 초기화
        self.vision = None
        self.hardware = None
        self.job_manager = JobManager() # 여기서 파일은 읽어왔는데...
        self.navigator = None
        self.logic = None
        
        self.SCALE_FACTOR = 2.0

        # === 레이아웃 ===
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 상단 패널 (미니맵)
        top_layout = QVBoxLayout()
        self.screen_box = QGroupBox("Live View")
        screen_layout = QVBoxLayout()
        self.screen_label = QLabel("시스템 준비 중...")
        self.screen_label.setAlignment(Qt.AlignCenter)
        self.screen_label.setStyleSheet("background-color: #111; border: 1px solid #555;")
        self.screen_label.setMinimumSize(400, 250) 
        self.screen_label.mousePressEvent = self.on_minimap_click
        screen_layout.addWidget(self.screen_label)
        self.screen_box.setLayout(screen_layout)
        top_layout.addWidget(self.screen_box)

        self.status_label = QLabel("시스템 대기 중...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; background: #eee; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.status_label)

        main_layout.addLayout(top_layout, stretch=4)

        # 하단 패널 (탭)
        self.tabs = QTabWidget()
        self.tab_home = HomeTab()
        self.tab_map = MapTab()
        self.tab_setup = SetupTab()

        self.tabs.addTab(self.tab_home, "홈 (실행)")
        self.tabs.addTab(self.tab_map, "맵 에디터")
        self.tabs.addTab(self.tab_setup, "설정")

        main_layout.addWidget(self.tabs, stretch=6)

        self.timer = QTimer()
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update_loop)

    def set_modules(self, hardware, vision):
        self.hardware = hardware
        self.vision = vision
        self.navigator = Navigator(hardware, self.job_manager)
        self.logic = HuntingManager(hardware, vision, self.navigator, self.job_manager)
        
        self.tab_home.set_logic(self.logic) 
        self.tab_home.set_vision(vision)
        
        self.tab_setup.set_job_manager(self.job_manager)
        self.tab_setup.set_hardware(hardware) # [추가됨]
        
        self.timer.start()
        print("[Main] 시스템 가동 시작")

    def update_loop(self):
        if not self.vision: return

        img = self.vision.get_cropped_minimap()
        if img is None:
            self.screen_label.setText("미니맵 찾는 중...")
            return

        player_pos = self.vision.get_player_position()
        if player_pos:
            cx, cy = player_pos
            cv2.circle(img, (cx, cy), 4, (0, 0, 255), -1)
            cv2.rectangle(img, (cx-10, cy-10), (cx+10, cy+10), (0, 0, 255), 1)

        current_idx = self.tabs.currentIndex()
        if current_idx == 0: 
            self.tab_home.draw_overlay(img) 
            if self.logic.is_running:
                self.status_label.setText(f"상태: {self.logic.state}")
            else:
                self.status_label.setText("대기 중 (시작 버튼을 누르세요)")

        elif current_idx == 1: 
            self.tab_map.draw_overlay(img)
            self.status_label.setText(f"맵 편집 모드: {self.tab_map.info_text}")

        elif current_idx == 2: 
            self.status_label.setText("설정 변경 중...")

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = img_rgb.shape
        q_img = QImage(img_rgb.data, w, h, c * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        scaled_w = int(w * self.SCALE_FACTOR)
        scaled_h = int(h * self.SCALE_FACTOR)
        self.screen_label.setPixmap(pixmap.scaled(scaled_w, scaled_h, Qt.KeepAspectRatio, Qt.FastTransformation))

    def on_minimap_click(self, event):
        if not self.screen_label.pixmap(): return

        pixmap = self.screen_label.pixmap()
        offset_x = (self.screen_label.width() - pixmap.width()) // 2
        offset_y = (self.screen_label.height() - pixmap.height()) // 2
        click_x = event.pos().x() - offset_x
        click_y = event.pos().y() - offset_y

        if 0 <= click_x < pixmap.width() and 0 <= click_y < pixmap.height():
            real_x = int(click_x / self.SCALE_FACTOR)
            real_y = int(click_y / self.SCALE_FACTOR)
            
            if self.tabs.currentIndex() == 1:
                self.tab_map.handle_click(real_x, real_y)