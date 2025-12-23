import cv2
import numpy as np
import win32gui, win32ui, win32con
from ctypes import windll
from ultralytics import YOLO
import time
import threading

class VisionSystem:
    def __init__(self, minimap_model_path):
        print("[Vision] 시각 시스템 초기화...")
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
        
        # [최적화] 캐싱
        self.last_inference_time = 0
        self.cached_detections = []
        self.cache_duration = 0.05

        # [추가] 미니맵 고정 스위치
        self.is_minimap_locked = False
        self.lock = threading.RLock() # 2. RLock 생성 (중요!)

    # ... (find_window, capture_screen 함수는 기존 유지) ...
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
            left, top, right, bot = win32gui.GetWindowRect(self.hwnd)
            w, h = right - left, bot - top
            if w <= 100 or h <= 100: return None

            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            result = windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)
            if result == 1:
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                img = np.frombuffer(bmpstr, dtype='uint8')
                img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(self.hwnd, hwndDC)
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(self.hwnd, hwndDC)
                return None
        except: return None

    # [수정] 락 걸려있으면 재탐색 안 함
    def find_minimap_area(self):
        if self.is_minimap_locked and self.minimap_rect:
            return True # 이미 잠겨있고 좌표도 있으면 패스

        full_img = self.capture_screen()
        if full_img is None: return False
        
        roi = full_img[0:400, 0:500] 
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
        with self.lock: # 3. 락 걸기
            current_time = time.time()
                # [수정] 락 안 걸려있을 때만 주기적 재스캔
            if not self.is_minimap_locked:
                if self.minimap_rect is None or (current_time - self.last_scan_time > self.scan_interval):
                    self.find_minimap_area()
                    self.last_scan_time = current_time
            
            full_img = self.capture_screen()
            if full_img is None or self.minimap_rect is None: return None

            x, y, w, h = self.minimap_rect
            if y+h > full_img.shape[0] or x+w > full_img.shape[1]: return None
            return full_img[y:y+h, x:x+w]

    # ... (detect_objects, get_player_position 등 기존 유지) ...
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
        
