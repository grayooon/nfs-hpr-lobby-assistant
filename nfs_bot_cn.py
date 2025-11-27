"""
NFS Hot Pursuit Remastered Autopilot Bot (Lobby Assistant)
----------------------------------------
A Python-based computer vision bot for automating matchmaking and car selection 
in Need for Speed: Hot Pursuit Remastered.
专为《极品飞车：热力追踪 重制版》设计的 Python 计算机视觉辅助脚本，
用于自动化匹配和选车。

Features / 主要功能:
- 支持 OBS 虚拟摄像机（解决全屏游戏黑屏问题）。
- 健壮的有限状态机逻辑。
- 智能中断（检测玩家手动输入）。
- 资源高效（睡眠/深度休眠模式）。
- 灰度匹配技术以提高识别准确率。

Author: [Your Name/Handle]
Version: 1.0 (Release Candidate)
License: MIT
"""

import os
import time
import random
from datetime import datetime

# 第三方库导入
import cv2
import numpy as np
import pydirectinput
import keyboard

# ================= Configuration (配置区) =================

# 摄像头与视觉配置
CAMERA_ID = 0  # 摄像头ID（OBS虚拟摄像头通常为0）
MATCH_THRESHOLD = 0.70  # 相似度阈值 (0.0 - 1.0)
ENABLE_DEBUG_WINDOW_DEFAULT = False  # 默认调试窗口状态

# 时间配置（秒）
INTERVAL_NORMAL = 0.5   # 常规扫描间隔
INTERVAL_RAPID = 0.3    # 连点间隔
INTERVAL_CONFIRM = 0.5  # 确认间隔
KEY_PRESS_DURATION = 0.05 # 按键按下持续时间（确保游戏识别的关键）

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(SCRIPT_DIR, "assets")

# 车辆选择逻辑（配置：对应图片后缀 -> 右移次数）
# '0' 代表直接按空格键选中。
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
        """打印带时间戳的日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

class NFSBot:
    def __init__(self):
        # 初始状态：关闭
        # 状态：OFF, ACTIVE (运行), SLEEP (低功耗), STOPPED (深度休眠)
        self.mode = "OFF" 
        self.cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_DSHOW)
        
        # 强制设置1080p分辨率以匹配素材尺寸
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # 加载图片素材
        self.templates = self.load_assets()
        
        # 状态变量
        self.last_scan_time = 0
        self.last_action_time = 0
        self.interrupted = False
        self.show_debug_window = ENABLE_DEBUG_WINDOW_DEFAULT

        Logger.log(f"NFS Autopilot Bot v1.0 已初始化。")
        Logger.log(f"资源目录: {ASSET_DIR}")
        Logger.log("控件: [7] 运行 | [9] 睡眠 | [0] 深度休眠 (停止)")
        Logger.log("调试视图: 按 [V] 切换。")

    def load_assets(self):
        """
        从 assets 目录加载所有 PNG 素材。
        """
        templates = {}
        # 必需的截图文件名列表
        required_files = [
            "main_page.png", "online_main_page.png", 
            "status_waiting_joinin.png", "status_success_joinin.png",
            "select_car.png", "select_color.png",
            "policecar_a.png", "policecar_b.png", "policecar_c.png", "policecar_d.png", "policecar_e.png",
            "racercar_a.png", "racercar_b.png", "racercar_c.png", "racercar_d.png", "racercar_e.png"
        ]
        
        if not os.path.exists(ASSET_DIR):
            os.makedirs(ASSET_DIR)
            Logger.log(f"[错误] 未找到素材文件夹: {ASSET_DIR}")
            return {}

        count = 0
        for filename in required_files:
            path = os.path.join(ASSET_DIR, filename)
            if os.path.exists(path):
                # 读取图片
                img = cv2.imread(path)
                templates[filename] = img
                count += 1
            else:
                # 忽略缺失文件
                pass 
        
        Logger.log(f"素材已加载: {count}/{len(required_files)}")
        return templates

    def get_frame(self):
        """
        从摄像头捕获单帧画面。
        """
        if not self.cap.isOpened(): return None
        ret, frame = self.cap.read()
        if not ret: return None
        return frame
    
    def flush_camera_buffer(self):
        """
        读取并丢弃多帧以清空内部缓存。
        在长时间睡眠后执行此操作至关重要，可防止处理旧画面（解决画面延迟问题）。
        """
        for _ in range(5):
            self.cap.read()

    def detect(self, frame, template_name, debug_draw=True):
        """
        执行模板匹配，使用灰度转换以增强对光影/颜色变化的鲁棒性。
        """
        if template_name not in self.templates: return False, 0.0
        
        template = self.templates[template_name]
        if template is None: return False, 0.0

        # 将当前画面和模板都转换为灰度图
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if len(template.shape) == 3:
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            gray_template = template

        # 执行匹配
        res = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        found = (max_val >= MATCH_THRESHOLD)

        # 调试可视化（在原始彩色画面上绘制）
        if debug_draw and max_val > 0.65:
            h, w = template.shape[:2]
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            # 绿色表示匹配，红色表示疑似
            color = (0, 255, 0) if found else (0, 0, 255) 
            cv2.rectangle(frame, top_left, bottom_right, color, 2)
            cv2.putText(frame, f"{template_name} ({max_val:.2f})", 
                       (top_left[0], top_left[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return found, max_val

    def detect_any(self, frame, key_list):
        """
        从模板列表中寻找最佳匹配项。
        """
        best_match = None
        best_score = 0
        for key in key_list:
            found, score = self.detect(frame, key, debug_draw=True)
            if found and score > best_score:
                best_score = score
                best_match = key
        return best_match

    # --- 输入逻辑 ---

    def press_key(self, key, count=1, interval=0.1):
        """
        模拟按键，并保持特定持续时间以确保游戏能检测到。
        """
        for _ in range(count):
            if self.check_interrupt(): 
                return False 
            
            # 按下 -> 保持 -> 松开
            pydirectinput.keyDown(key)
            time.sleep(KEY_PRESS_DURATION) 
            pydirectinput.keyUp(key)
            
            time.sleep(interval)
        return True

    def check_interrupt(self):
        """
        检查玩家是否进行人工干预（左/右方向键）。
        """
        if keyboard.is_pressed('left') or keyboard.is_pressed('right'):
            if not self.interrupted:
                Logger.log("[中断] 检测到玩家操作！切换至人工接管模式。")
                self.interrupted = True
            return True
        return False

    def get_clicks_from_config(self, car_img_name, role_type):
        """
        解析配置，根据图片后缀获取点击次数。
        """
        try:
            suffix = car_img_name.split('_')[-1].replace('.png', '')
            if suffix in CAR_SELECTION_CONFIG[role_type]:
                return CAR_SELECTION_CONFIG[role_type][suffix]
            return 0
        except: return 0

    # --- 游戏逻辑 ---

    def logic_lobby_matchmaking(self, frame):
        """
        处理主页面和联机大厅的交互逻辑。
        """
        current_time = time.time()
        
        # 检测主页面
        is_main, _ = self.detect(frame, "main_page.png")
        if is_main:
            if current_time - self.last_action_time > 1.0:
                Logger.log("状态：主页面 -> 进入联机")
                pydirectinput.press('left')
                time.sleep(0.5)
                pydirectinput.press('space')
                self.last_action_time = current_time
            return

        # 检测在线大厅
        is_online, _ = self.detect(frame, "online_main_page.png")
        if is_online:
            if current_time - self.last_action_time > 2.0:
                Logger.log("状态：联机大厅 -> 开始匹配")
                pydirectinput.press('space')
                self.last_action_time = current_time
            return
            
        # 仅作视觉确认的被动检测
        self.detect(frame, "status_waiting_joinin.png")
        self.detect(frame, "status_success_joinin.png")

    def logic_car_selection(self, frame):
        """
        处理选车阶段逻辑。
        """
        is_select_car, _ = self.detect(frame, "select_car.png")
        
        if not is_select_car:
            # 补救：如果被中断，检查是否在选色界面
            if self.interrupted:
                is_color_ui, _ = self.detect(frame, "select_color.png")
                if is_color_ui: self.sequence_color_confirm_random()
            return

        if self.interrupted: return 

        # 扫描车辆类别
        police_list = [f"policecar_{c}.png" for c in ['a','b','c','d','e']]
        racer_list = [f"racercar_{c}.png" for c in ['a','b','c','d','e']]
        
        detected_police = self.detect_any(frame, police_list)
        detected_racer = self.detect_any(frame, racer_list)

        if detected_police: self.sequence_police(detected_police)
        elif detected_racer: self.sequence_racer(detected_racer)

    def sequence_police(self, car_img_name):
        """
        警察选车流程 + 深度休眠。
        """
        clicks = self.get_clicks_from_config(car_img_name, "POLICE")
        Logger.log(f"Police Detected: {car_img_name} -> 右移 {clicks}")
        
        if clicks > 0:
            if not self.press_key('right', clicks, INTERVAL_RAPID): return
            time.sleep(INTERVAL_CONFIRM)
        
        if not self.press_key('space', 1): return
        
        Logger.log("已选车，等待确认...")
        time.sleep(1.5)
        pydirectinput.press('shift')

        # 进入深度休眠
        Logger.log("确认。进入深度休眠 (40秒)...")
        self.mode = "STOPPED"
        cv2.destroyAllWindows()
        time.sleep(40.0) 
        
        self.flush_camera_buffer() # 唤醒后清空旧帧
        
        Logger.log("唤醒。切换至睡眠模式。")
        self.mode = "SLEEP"

    def sequence_racer(self, car_img_name):
        """
        赛车手选车流程（后续进入选色）。
        """
        clicks = self.get_clicks_from_config(car_img_name, "RACER")
        Logger.log(f"Racer Detected: {car_img_name} -> 右移 {clicks}")

        if clicks > 0:
            if not self.press_key('right', clicks, INTERVAL_RAPID): return
            time.sleep(INTERVAL_CONFIRM)
        
        if not self.press_key('space', 1): return
        Logger.log("赛车手已选。等待选色...")
        self.wait_for_color_and_confirm()

    def sequence_color_confirm_random(self):
        """
        随机选色 + 深度休眠。
        """
        Logger.log("正在随机选色...")
        shifts = random.randint(0, 9)
        pydirectinput.press('right', presses=shifts, interval=0.1)
        time.sleep(0.5)
        pydirectinput.press('shift')

        Logger.log("确认。进入深度休眠 (40秒)...")
        self.mode = "STOPPED"
        cv2.destroyAllWindows()
        time.sleep(40.0)
        
        self.flush_camera_buffer() # 清空旧帧
        
        Logger.log("唤醒。切换至睡眠模式。")
        self.interrupted = False
        self.mode = "SLEEP"

    def wait_for_color_and_confirm(self):
        """
        等待选色界面出现。
        """
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
        Logger.log("选色超时。切换至睡眠模式。")
        self.mode = "SLEEP"

    def run(self):
        while True:
            current_time = time.time()

            # 快捷键
            # 使用 7/9/0 以避开小键盘/方向键冲突
            if keyboard.is_pressed('7'):
                if self.mode != "ACTIVE":
                    self.mode = "ACTIVE"
                    self.interrupted = False
                    Logger.log(">>> [ACTIVE] 运行模式")
                time.sleep(0.2) 
            elif keyboard.is_pressed('9'):
                if self.mode != "SLEEP":
                    self.mode = "SLEEP"
                    Logger.log(">>> [SLEEP] 睡眠模式")
                time.sleep(0.2)
            elif keyboard.is_pressed('0'):
                if self.mode != "STOPPED":
                    self.mode = "STOPPED"
                    Logger.log(">>> [STOPPED] 深度休眠 (视觉关闭，仅响应按键)")
                    cv2.destroyAllWindows() 
                time.sleep(0.2)
            # --------------------------------------------------

            # 深度休眠拦截
            if self.mode == "STOPPED":
                time.sleep(0.1)
                continue

            frame = self.get_frame()
            if frame is None: continue

            # 模式逻辑
            if self.mode == "ACTIVE":
                # 按常规间隔扫描
                if current_time - self.last_scan_time > INTERVAL_NORMAL:
                    self.logic_lobby_matchmaking(frame)
                    self.logic_car_selection(frame)
                    self.last_scan_time = current_time

            elif self.mode == "SLEEP":
                # 每5秒扫描一次（低功耗）
                if current_time - self.last_scan_time > 5.0:
                    all_keys = self.templates.keys()
                    found_any = self.detect_any(frame, all_keys)
                    if found_any:
                        Logger.log(f"[自动唤醒] 检测到画面变化")
                        self.mode = "ACTIVE"
                        self.interrupted = False
                    self.last_scan_time = current_time

            # 调试窗口逻辑
            if keyboard.is_pressed('v'):
                self.show_debug_window = not self.show_debug_window
                Logger.log(f"调试窗口: {'开启' if self.show_debug_window else '关闭'}")
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