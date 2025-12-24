"""
프로젝트 전체에서 공유하는 전역 변수 및 모듈 저장소입니다.
import core.config as config 로 어디서든 접근 가능합니다.
"""

# === 상태 변수 ===
player_pos = None       # 캐릭터 좌표 (x, y)
minimap_img = None      # 현재 미니맵 이미지
enabled = False         # 봇 가동 여부 (True/False)
state = "IDLE"          # 현재 로직 상태 (예: HUNTING, RUNE_SOLVING)

# === 모듈 참조 (순환 참조 방지용) ===
# main_window.py에서 초기화 시점에 주입해줍니다.
hardware = None
vision = None
gui = None
job_manager = None
logic = None