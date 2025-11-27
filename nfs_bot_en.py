"""
NFS Hot Pursuit Remastered Autopilot Bot
----------------------------------------
A Python-based computer vision bot for automating matchmaking and car selection 
in Need for Speed: Hot Pursuit Remastered.

Features:
- OBS Virtual Camera support (bypasses full-screen black screen issues).
- Robust FSM (Finite State Machine) logic.
- Smart interruption (detects manual player input).
- CPU/GPU efficient (Sleep/Stopped modes).
- Grayscale matching for high accuracy.

Author: [Your Name/Handle]
Version: 3.2 (Release Candidate)
License: MIT
"""

import os
import time
import random
from datetime import datetime

# Third-party imports
import cv2
import numpy as np
import pydirectinput
import keyboard

# ================= Configuration (配置区) =================

# Camera & Vision
CAMERA_ID = 0
MATCH_THRESHOLD = 0.70  # 相似度阈值 (0.0 - 1.0)
ENABLE_DEBUG_WINDOW_DEFAULT = False

# Timing (Seconds)
INTERVAL_NORMAL = 0.5   # 常规扫描间隔
INTERVAL_RAPID = 0.3    # 连点间隔
INTERVAL_CONFIRM = 0.5  # 确认间隔
KEY_PRESS_DURATION = 0.05 # 按键按下持续时间 (关键: 防止游戏判定为长按)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(SCRIPT_DIR, "assets")

# Car Selection Logic (配置: 对应图片后缀 -> 右移次数)
# '0' means press SPACE directly.
CAR_SELECTION_CONFIG = {
    "POLICE": {
        "a": 7, "b": 6, "c": 10, "d": 1, "e": 0
    },
    "RACER": {
        "a": 7, "b": 5, "c": 16, "d": 12, "e": 1
    }
}

# ==========================================================

class Logger:
    @staticmethod
    def log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

class NFSBot:
    def __init__(self):
        self.mode = "OFF" # States: OFF, ACTIVE, SLEEP, STOPPED
        self.cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_DSHOW)
        
        # Force resolution to 1080p to match assets
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        self.templates = self.load_assets()
        
        # State variables
        self.last_scan_time = 0
        self.last_action_time = 0
        self.interrupted = False
        self.show_debug_window = ENABLE_DEBUG_WINDOW_DEFAULT

        Logger.log(f"NFS Autopilot Bot v3.2 Initialized.")
        Logger.log(f"Resource Directory: {ASSET_DIR}")
        Logger.log("Controls: [7] Run | [9] Sleep | [0] Deep Sleep (Stop)")
        Logger.log("Debug View: Press [V] to toggle.")

    def load_assets(self):
        """Loads all PNG assets from the assets directory."""
        templates = {}
        required_files = [
            "main_page.png", "online_main_page.png", 
            "status_waiting_joinin.png", "status_success_joinin.png",
            "select_car.png", "select_color.png",
            "policecar_a.png", "policecar_b.png", "policecar_c.png", "policecar_d.png", "policecar_e.png",
            "racercar_a.png", "racercar_b.png", "racercar_c.png", "racercar_d.png", "racercar_e.png"
        ]
        
        if not os.path.exists(ASSET_DIR):
            os.makedirs(ASSET_DIR)
            Logger.log(f"[Error] Assets folder not found: {ASSET_DIR}")
            return {}

        count = 0
        for filename in required_files:
            path = os.path.join(ASSET_DIR, filename)
            if os.path.exists(path):
                # Read image
                img = cv2.imread(path)
                templates[filename] = img
                count += 1
            else:
                # Silent fail for cleaner logs, or enable logging if debugging
                pass 
        
        Logger.log(f"Assets loaded: {count}/{len(required_files)}")
        return templates

    def get_frame(self):
        """Captures a single frame from the camera."""
        if not self.cap.isOpened(): return None
        ret, frame = self.cap.read()
        if not ret: return None
        return frame
    
    def flush_camera_buffer(self):
        """
        Reads and discards multiple frames to clear the internal buffer.
        Essential after long sleep periods to avoid processing old frames.
        """
        for _ in range(5):
            self.cap.read()

    def detect(self, frame, template_name, debug_draw=True):
        """
        Performs template matching using Grayscale conversion for robustness against color shifts.
        """
        if template_name not in self.templates: return False, 0.0
        
        template = self.templates[template_name]
        if template is None: return False, 0.0

        # Convert both frame and template to Grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if len(template.shape) == 3:
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            gray_template = template

        # Match
        res = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        found = (max_val >= MATCH_THRESHOLD)

        # Debug Visualization (Draw on original colored frame)
        if debug_draw and max_val > 0.65:
            h, w = template.shape[:2]
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            color = (0, 255, 0) if found else (0, 0, 255) # Green if match, Red if suspect
            cv2.rectangle(frame, top_left, bottom_right, color, 2)
            cv2.putText(frame, f"{template_name} ({max_val:.2f})", 
                       (top_left[0], top_left[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return found, max_val

    def detect_any(self, frame, key_list):
        """Finds the best match from a list of template keys."""
        best_match = None
        best_score = 0
        for key in key_list:
            found, score = self.detect(frame, key, debug_draw=True)
            if found and score > best_score:
                best_score = score
                best_match = key
        return best_match

    # --- Input Logic ---

    def press_key(self, key, count=1, interval=0.1):
        """Simulates key press with a specific duration to ensure game detection."""
        for _ in range(count):
            if self.check_interrupt(): 
                return False 
            
            pydirectinput.keyDown(key)
            time.sleep(KEY_PRESS_DURATION) 
            pydirectinput.keyUp(key)
            
            time.sleep(interval)
        return True

    def check_interrupt(self):
        """Checks for manual player intervention (Left/Right keys)."""
        if keyboard.is_pressed('left') or keyboard.is_pressed('right'):
            if not self.interrupted:
                Logger.log("[Interrupt] Player detected! Switching to manual mode.")
                self.interrupted = True
            return True
        return False

    def get_clicks_from_config(self, car_img_name, role_type):
        try:
            suffix = car_img_name.split('_')[-1].replace('.png', '')
            if suffix in CAR_SELECTION_CONFIG[role_type]:
                return CAR_SELECTION_CONFIG[role_type][suffix]
            return 0
        except: return 0

    # --- Game Logic ---

    def logic_lobby_matchmaking(self, frame):
        current_time = time.time()
        
        # Check Main Page
        is_main, _ = self.detect(frame, "main_page.png")
        if is_main:
            if current_time - self.last_action_time > 1.0:
                Logger.log("State: Main Page -> Entering Online")
                pydirectinput.press('left')
                time.sleep(0.5)
                pydirectinput.press('space')
                self.last_action_time = current_time
            return

        # Check Online Page
        is_online, _ = self.detect(frame, "online_main_page.png")
        if is_online:
            if current_time - self.last_action_time > 2.0:
                Logger.log("State: Online Lobby -> Matchmaking")
                pydirectinput.press('space')
                self.last_action_time = current_time
            return
            
        # Passive detection for visual confirmation only
        self.detect(frame, "status_waiting_joinin.png")
        self.detect(frame, "status_success_joinin.png")

    def logic_car_selection(self, frame):
        is_select_car, _ = self.detect(frame, "select_car.png")
        
        if not is_select_car:
            # Fallback: Check for color selection if interrupted
            if self.interrupted:
                is_color_ui, _ = self.detect(frame, "select_color.png")
                if is_color_ui: self.sequence_color_confirm_random()
            return

        if self.interrupted: return 

        police_list = [f"policecar_{c}.png" for c in ['a','b','c','d','e']]
        racer_list = [f"racercar_{c}.png" for c in ['a','b','c','d','e']]
        
        detected_police = self.detect_any(frame, police_list)
        detected_racer = self.detect_any(frame, racer_list)

        if detected_police: self.sequence_police(detected_police)
        elif detected_racer: self.sequence_racer(detected_racer)

    def sequence_police(self, car_img_name):
        clicks = self.get_clicks_from_config(car_img_name, "POLICE")
        Logger.log(f"Police Detected: {car_img_name} -> Right {clicks}")
        
        if clicks > 0:
            if not self.press_key('right', clicks, INTERVAL_RAPID): return
            time.sleep(INTERVAL_CONFIRM)
        
        if not self.press_key('space', 1): return
        
        Logger.log("Car selected. Waiting for confirm...")
        time.sleep(1.5)
        pydirectinput.press('shift')

        Logger.log("Confirmed. Entering Deep Sleep (40s)...")
        self.mode = "STOPPED"
        cv2.destroyAllWindows()
        time.sleep(40.0) 
        
        self.flush_camera_buffer() # Clear old frames
        
        Logger.log("Wake up. Switching to SLEEP mode.")
        self.mode = "SLEEP"

    def sequence_racer(self, car_img_name):
        clicks = self.get_clicks_from_config(car_img_name, "RACER")
        Logger.log(f"Racer Detected: {car_img_name} -> Right {clicks}")

        if clicks > 0:
            if not self.press_key('right', clicks, INTERVAL_RAPID): return
            time.sleep(INTERVAL_CONFIRM)
        
        if not self.press_key('space', 1): return
        Logger.log("Racer selected. Waiting for color selection...")
        self.wait_for_color_and_confirm()

    def sequence_color_confirm_random(self):
        Logger.log("Selecting random paint...")
        shifts = random.randint(0, 9)
        pydirectinput.press('right', presses=shifts, interval=0.1)
        time.sleep(0.5)
        pydirectinput.press('shift')

        Logger.log("Confirmed. Entering Deep Sleep (40s)...")
        self.mode = "STOPPED"
        cv2.destroyAllWindows()
        time.sleep(40.0)
        
        self.flush_camera_buffer() # Clear old frames
        
        Logger.log("Wake up. Switching to SLEEP mode.")
        self.interrupted = False
        self.mode = "SLEEP"

    def wait_for_color_and_confirm(self):
        timeout = 8.0 
        start = time.time()
        while time.time() - start < timeout:
            frame = self.get_frame()
            if frame is None: continue
            
            is_color, _ = self.detect(frame, "select_color.png", debug_draw=True)
            if is_color:
                self.sequence_color_confirm_random()
                return
            time.sleep(0.1)
        Logger.log("Color selection timeout. Switching to SLEEP.")
        self.mode = "SLEEP"

    def run(self):
        while True:
            current_time = time.time()

            # --- Hotkeys (Safe from Numpad/Arrow conflicts) ---
            if keyboard.is_pressed('7'):
                if self.mode != "ACTIVE":
                    self.mode = "ACTIVE"
                    self.interrupted = False
                    Logger.log(">>> [ACTIVE] Running Mode")
                time.sleep(0.2) 
            elif keyboard.is_pressed('9'):
                if self.mode != "SLEEP":
                    self.mode = "SLEEP"
                    Logger.log(">>> [SLEEP] Sleep Mode")
                time.sleep(0.2)
            elif keyboard.is_pressed('0'):
                if self.mode != "STOPPED":
                    self.mode = "STOPPED"
                    Logger.log(">>> [STOPPED] Deep Sleep (Visuals Off, Keys Only)")
                    cv2.destroyAllWindows() 
                time.sleep(0.2)
            # --------------------------------------------------

            # Deep Sleep Barrier
            if self.mode == "STOPPED":
                time.sleep(0.1)
                continue

            frame = self.get_frame()
            if frame is None: continue

            # --- Mode Logic ---
            if self.mode == "ACTIVE":
                if current_time - self.last_scan_time > INTERVAL_NORMAL:
                    self.logic_lobby_matchmaking(frame)
                    self.logic_car_selection(frame)
                    self.last_scan_time = current_time

            elif self.mode == "SLEEP":
                # Scan every 5 seconds
                if current_time - self.last_scan_time > 5.0:
                    all_keys = self.templates.keys()
                    found_any = self.detect_any(frame, all_keys)
                    if found_any:
                        Logger.log(f"[Auto-Wake] Detected {found_any}")
                        self.mode = "ACTIVE"
                        self.interrupted = False
                    self.last_scan_time = current_time

            # --- Debug Window Logic ---
            if keyboard.is_pressed('v'):
                self.show_debug_window = not self.show_debug_window
                Logger.log(f"Debug Window: {'ON' if self.show_debug_window else 'OFF'}")
                time.sleep(0.3) 
                if not self.show_debug_window:
                    cv2.destroyAllWindows()

            if self.show_debug_window:
                cv2.imshow('NFS Bot Debug (Press V to toggle)', frame)
                cv2.waitKey(1)

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    bot = NFSBot()
    bot.run()