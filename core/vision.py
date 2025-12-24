import cv2
import numpy as np
import win32gui
import mss
from ultralytics import YOLO
import time
import threading
import ctypes

# 고해상도 모니터(DPI) 인식 설정
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

class VisionSystem:
    def __init__(self, minimap_model_path):
        print("[Vision] 시각 시스템 초기화 (MSS 고속 캡처 모드)...")
        try:
            self.model_minimap = YOLO(minimap_model_path)
        except Exception as e:
            self.model_minimap = None

        self.hwnd = None         
        self.minimap_rect = None 
        
        self.last_scan_time = 0
        self.scan_interval = 2.0 
        
        self.pending_rect = None
        self.stability_count = 0
        
        # 캐싱
        self.last_inference_time = 0
        self.cached_detections = []
        self.cache_duration = 0.05

        # 미니맵 고정 스위치
        self.is_minimap_locked = False
        self.lock = threading.RLock()
        
        # [수정] __init__에서 self.sct를 생성하지 않습니다. (스레드 충돌 방지)

    def find_window(self, window_name="MapleStory"):
        candidate_hwnds = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title == window_name:
                    rect = win32gui.GetWindowRect(hwnd)
                    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
                    candidate_hwnds.append((hwnd, area))
        win32gui.EnumWindows(callback, None)
        if not candidate_hwnds: return False
        candidate_hwnds.sort(key=lambda x: x[1], reverse=True)
        best_hwnd = candidate_hwnds[0][0]
        if self.hwnd != best_hwnd:
            self.hwnd = best_hwnd
        return True

    def capture_screen(self):
        if not self.hwnd:
            if not self.find_window(): return None
        
        try:
            # 1. 윈도우 클라이언트 영역 크기 계산
            rect = win32gui.GetClientRect(self.hwnd)
            if not rect: return None
            
            client_w = rect[2] - rect[0]
            client_h = rect[3] - rect[1]
            
            if client_w <= 10 or client_h <= 10: return None

            # 2. 화면 좌표 변환
            client_point = win32gui.ClientToScreen(self.hwnd, (0, 0))
            client_x, client_y = client_point

            monitor = {
                "top": client_y, 
                "left": client_x, 
                "width": client_w, 
                "height": client_h
            }
            
            # [수정] with 문을 사용하여 스레드 안전성 확보
            with mss.mss() as sct:
                sct_img = sct.grab(monitor)
                img = np.array(sct_img)
                # mss(BGRA) -> OpenCV(BGR)
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        except Exception as e:
            # print(f"[Vision] 캡처 오류: {e}") 
            return None

    def find_minimap_area(self):
        if self.is_minimap_locked and self.minimap_rect:
            return True 

        full_img = self.capture_screen()
        if full_img is None: return False
        
        roi_h, roi_w = min(400, full_img.shape[0]), min(500, full_img.shape[1])
        roi = full_img[0:roi_h, 0:roi_w] 
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_area = 0
        best_rect = None

        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            if 4 <= len(approx) <= 8:
                area = cv2.contourArea(contour)
                if area > 10000:
                    x, y, w, h = cv2.boundingRect(approx)
                    if w > h and area > max_area:
                        max_area = area
                        best_rect = (x, y, w, h)

        if best_rect:
            new_x, new_y, new_w, new_h = best_rect
            if self.minimap_rect is None:
                self.minimap_rect = best_rect
                self.stability_count = 0
                return True
            
            old_x, old_y, old_w, old_h = self.minimap_rect
            is_changed = (abs(old_w - new_w) > 5) or (abs(old_h - new_h) > 5) or \
                         (abs(old_x - new_x) > 5) or (abs(old_y - new_y) > 5)
            
            if is_changed:
                if self.pending_rect == best_rect:
                    self.stability_count += 1
                else:
                    self.pending_rect = best_rect
                    self.stability_count = 1
                
                if self.stability_count >= 2:
                    self.minimap_rect = best_rect
                    self.stability_count = 0
                    self.pending_rect = None
                    return True
            else:
                self.stability_count = 0
                self.pending_rect = None
                return True
        return False

    def get_cropped_minimap(self):
        with self.lock:
            current_time = time.time()
            if not self.is_minimap_locked:
                if self.minimap_rect is None or (current_time - self.last_scan_time > self.scan_interval):
                    self.find_minimap_area()
                    self.last_scan_time = current_time
            
            full_img = self.capture_screen()
            if full_img is None or self.minimap_rect is None: return None

            x, y, w, h = self.minimap_rect
            if y+h > full_img.shape[0] or x+w > full_img.shape[1]: return None
            
            return full_img[y:y+h, x:x+w]

    def detect_objects(self):
        current_time = time.time()
        if current_time - self.last_inference_time < self.cache_duration:
            if self.cached_detections is not None:
                return self.cached_detections

        cropped = self.get_cropped_minimap()
        if cropped is None or self.model_minimap is None:
            return []

        results = self.model_minimap(cropped, verbose=False, conf=0.2)
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                label = self.model_minimap.names[int(box.cls[0])]
                conf = float(box.conf[0])
                detections.append({
                    "label": label, "x": int(cx), "y": int(cy),
                    "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2), "conf": conf
                })
        
        self.cached_detections = detections
        self.last_inference_time = current_time
        return detections

    def get_player_position(self):
        with self.lock:
            detections = self.detect_objects()
            for d in detections:
                label = d['label'].lower()
                if label in ['char', 'player', 'character', 'me']:
                    return (d['x'], d['y'])
            return None