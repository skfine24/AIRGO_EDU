import sys
import os
import subprocess
import time

# pyserial 라이브러리 체크 및 자동 설치
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial 라이브러리가 없습니다. 설치를 시작합니다...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyserial"])
        import serial
        import serial.tools.list_ports
    except Exception as e:
        print(f"라이브러리 설치 중 오류 발생: {e}")
        sys.exit(1)

import tkinter as tk
from tkinter import messagebox, scrolledtext
import tkinter.font as tkfont
import threading
from datetime import datetime
import webbrowser
import ctypes

# EXE 내부 리소스 경로 탐색 함수 (반드시 필요)
def resource_path(relative_path):
    try:
        # PyInstaller로 빌드된 경우 임시 폴더 경로를 참조
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DroneController:
    def __init__(self, root):
        self.root = root
        self.version = "v.2.14" 
        self.app_name = f"SYUBEA Drone Controller {self.version}"
        self.root.title(self.app_name)
        
        # [1] 윈도우 작업 표시줄 아이콘 강제 적용 (AppID 고유화)
        try:
            # 이 ID가 다르면 윈도우는 별개의 프로그램으로 인식하여 아이콘을 새로 그립니다.
            myappid = u'syubea.drone.controller.v214' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass

        # [2] 아이콘 파일 설정
        self.icon_name = "icon.ico" 
        self.icon_full_path = resource_path(self.icon_name)
        
        if os.path.exists(self.icon_full_path):
            try:
                # 창 제목줄 아이콘
                self.root.iconbitmap(self.icon_full_path)
                # 작업 표시줄 및 전체 창 아이콘 강제 호출
                img = tk.PhotoImage(file=self.icon_full_path)
                self.root.tk.call('wm', 'iconphoto', self.root._w, img)
            except:
                pass

        # 제어 변수 및 상태 초기화
        self.cmd_queue = [] 
        self.execution_active = False
        self.immediate_mode = True  
        self.speed_step = 1
        self.ser = None
        self.buttons = []          
        self.emergency_btn = None  
        self.current_lang = "KO"
        self.que_count = 1
        self.is_moving = False  
        self.last_click_time = 0
        self.speed_display_timer = None 

        # 폰트 설정
        available_fonts = tkfont.families()
        self.default_font_family = "나눔고딕" if "나눔고딕" in available_fonts else "맑은 고딕" if "맑은 고딕" in available_fonts else "Arial"

        self.root.geometry("1300x900") 
        self.root.resizable(True, True) 

        # 다국어 데이터 (유지)
        self.languages = {
            "KO": {
                "port_cfg": "시리얼 포트 설정", "connect": "연결", "disconnect": "연결 끊기", "refresh": "새로고침",
                "st_connected": "연결됨", "st_waiting": "연결대기",
                "param_cfg": "이동 파라미터 설정", "power": "레버 값 (강도): 20 ~ 500", "time": "이동 시간 (ms): 100 ~ 10000",
                "sys_ctrl": "시스템 제어", "mode2": "조종 모드 2", "start": "시동", "stop": "정지", "takeoff": "이륙", "land": "착륙",
                "left_lever": "좌측 레버 (Throttle/Yaw)", "up": "상승", "down": "하강", "ccw": "좌회전", "cw": "우회전",
                "right_lever": "우측 레버 (Pitch/Roll)", "forward": "전진", "back": "후진", "left": "좌측 이동", "right": "우측 이동",
                "func": "특수 기능", "bind": "드론 바인딩", "emergency": "비상정지", "battery": "배터리 확인", "led": "LED변경", "gyro": "자이로 리셋", "headless": "헤드리스",
                "speed": "속도", "hover": "호버링\n(대기)", "status_title": "명령어 로그", 
                "wait": "준비 완료", "send": "전송", "recv": "수신",
                "mode_inst": "조종기 모드", "mode_que": "코딩 모드", "que_title": "실행 모드", "run_que": "▶ 코딩 실행 ◀", "stop_que": "■ 코딩 중단 ■", "clear_que": "목록 지우기",
                "tm_wait_rx": "수신 대기", "tm_stable": "안정화 중", "tm_ready": "코딩 모드", "tm_done": "완료", "tm_stop": "중단됨",
                "mode_label_inst": "조종기 모드", "speed_disp": "속도 {}단"
            },
            "EN": { "port_cfg": "Serial Port Setup", "connect": "Connect", "disconnect": "Disconnect", "refresh": "Refresh", "st_connected": "Connected", "st_waiting": "Waiting", "param_cfg": "Movement Parameters", "power": "Power: 20 ~ 500", "time": "Time (ms): 100 ~ 10000", "sys_ctrl": "System Control", "mode2": "Mode 2 Control", "start": "Start", "stop": "Stop", "takeoff": "Takeoff", "land": "Land", "left_lever": "Left Lever", "up": "Up", "down": "Down", "ccw": "CCW", "cw": "CW", "right_lever": "Right Lever", "forward": "Forward", "back": "Back", "left": "Left", "right": "Right", "func": "Special Func", "bind": "Binding", "emergency": "EMERGENCY", "battery": "Battery", "led": "LED Color", "gyro": "Gyro Reset", "headless": "Headless", "speed": "Speed", "hover": "Hovering", "status_title": "Log", "wait": "Ready", "send": "TX", "recv": "RX", "mode_inst": "RC Mode", "mode_que": "Coding Mode", "que_title": "Execution Mode", "run_que": "▶ RUN ◀", "stop_que": "■ STOP ■", "clear_que": "Clear List", "tm_wait_rx": "WAIT RX", "tm_stable": "STABLE", "tm_ready": "CODING MODE", "tm_done": "DONE", "tm_stop": "STOPPED", "mode_label_inst": "RC MODE", "speed_disp": "SPEED {}" },
            "ZH": { "port_cfg": "串口设置", "connect": "连接", "disconnect": "断开连接", "refresh": "刷新", "st_connected": "已连接", "st_waiting": "等待连接", "param_cfg": "移动参数设置", "power": "杆值: 20 ~ 500", "time": "时间: 100 ~ 10000", "sys_ctrl": "系统控制", "mode2": "遥控模式 2", "start": "启动", "stop": "停止", "takeoff": "起飞", "land": "降落", "left_lever": "左摇杆", "up": "上升", "down": "下降", "ccw": "左旋转", "cw": "右旋转", "right_lever": "右摇杆", "forward": "前进", "back": "后退", "left": "向左移动", "right": "向右移动", "func": "特殊功能", "bind": "绑定", "emergency": "紧急停止", "battery": "电池", "led": "LED", "gyro": "复位", "headless": "无头模式", "speed": "速度", "hover": "悬停", "status_title": "日志", "wait": "准备", "send": "发送", "recv": "接收", "mode_inst": "遥控模式", "mode_que": "编程模式", "que_title": "运行模式", "run_que": "▶ 运行 ◀", "stop_que": "■ 停止 ■", "clear_que": "清除", "tm_wait_rx": "等待", "tm_stable": "稳定中", "tm_ready": "编程", "tm_done": "完成", "tm_stop": "停止", "mode_label_inst": "遥控模式", "speed_disp": "速度 {}档" },
            "JA": { "port_cfg": "シリアル設定", "connect": "接続", "disconnect": "切断", "refresh": "更新", "st_connected": "接続中", "st_waiting": "接続待機", "param_cfg": "移動パラメータ設定", "power": "レバー値 (強度): 20 ~ 500", "time": "移動時間 (ms): 100 ~ 10000", "sys_ctrl": "システム制御", "mode2": "操作モード 2", "start": "始動", "stop": "停止", "takeoff": "離陸", "land": "着陸", "left_lever": "左レバー (Throttle/Yaw)", "up": "上昇", "down": "下降", "ccw": "左旋回", "cw": "右旋回", "right_lever": "右レバー (Pitch/Roll)", "forward": "前進", "back": "後退", "left": "左移動", "right": "右移動", "func": "特殊機能", "bind": "バインド", "emergency": "非常停止", "battery": "バッテリー確認", "led": "LED変更", "gyro": "ジャイロリ셋", "headless": "ヘッドレス", "speed": "速度", "hover": "ホバリング\n(待機)", "status_title": "ログ", "wait": "準備完了", "send": "送信", "recv": "受信", "mode_inst": "コントローラ", "mode_que": "コーディング", "que_title": "実行モード", "run_que": "▶ 実行 ◀", "stop_que": "■ 停止 ■", "clear_que": "クリア", "tm_wait_rx": "受信待機", "tm_stable": "安定化中", "tm_ready": "コーディング", "tm_done": "完了", "tm_stop": "停止", "mode_label_inst": "操作モード", "speed_disp": "速度 {}段階" },
            "VI": { "port_cfg": "Thiết lập cổng", "connect": "Kết nối", "disconnect": "Ngắt", "refresh": "Tải lại", "st_connected": "Đã nối", "st_waiting": "Chờ", "param_cfg": "Thông số", "power": "Cường độ: 20 ~ 500", "time": "Thời gian: 100 ~ 10000", "sys_ctrl": "Hệ thống", "mode2": "Chế độ 2", "start": "Bắt đầu", "stop": "Dừng", "takeoff": "Cất cánh", "land": "Hạ cánh", "left_lever": "Cần trái", "up": "Lên", "down": "Xuống", "ccw": "Xoay trái", "cw": "Xoay phải", "right_lever": "Cần phải", "forward": "Tiến", "back": "Lùi", "left": "Trái", "right": "Phải", "func": "Chức năng", "bind": "Nối Drone", "emergency": "KHẨN CẤP", "battery": "Pin", "led": "LED", "gyro": "Reset", "headless": "Headless", "speed": "Tốc độ", "hover": "Chờ", "status_title": "Nhật ký", "wait": "Sẵn sàng", "send": "Gửi", "recv": "Nhận", "mode_inst": "Chế độ lái", "mode_que": "Chế độ Code", "que_title": "Thực thi", "run_que": "▶ CHẠY ◀", "stop_que": "■ DỪNG ■", "clear_que": "Xóa", "tm_wait_rx": "Chờ nhận", "tm_stable": "Ổn định", "tm_ready": "CODE", "tm_done": "XONG", "tm_stop": "DỪNG", "mode_label_inst": "LÁI", "speed_disp": "Tốc độ {}" }
        }

        self.setup_menu()
        self.setup_ui()
        self.change_lang("KO")
        self.update_button_states(False)
        self.root.bind("<space>", self.on_space_press)

    def on_space_press(self, event): self.send_emergency()

    def setup_ui(self):
        f_normal = (self.default_font_family, 10); f_bold = (self.default_font_family, 10, "bold")
        f_small = (self.default_font_family, 9); f_small_bold = (self.default_font_family, 9, "bold")
        self.f_timer = (self.default_font_family, 44, "bold") 
        self.left_ui_frame = tk.Frame(self.root); self.left_ui_frame.pack(side="left", fill="both", expand=True)
        self.conn_frame = tk.LabelFrame(self.left_ui_frame, font=f_normal); self.conn_frame.pack(fill="x", padx=10, pady=2)
        self.port_entry = tk.Entry(self.conn_frame, width=12, font=f_normal); self.port_entry.pack(side="left", padx=10, pady=5)
        auto_port = self.find_ch340_port(); self.port_entry.insert(0, auto_port if auto_port else "COM3")
        self.conn_btn = tk.Button(self.conn_frame, command=self.toggle_serial, bg="lightblue", font=f_bold); self.conn_btn.pack(side="left", padx=5)
        self.refresh_btn = tk.Button(self.conn_frame, command=self.refresh_port, font=f_normal); self.refresh_btn.pack(side="left", padx=5)
        self.status_text_label = tk.Label(self.conn_frame, font=(self.default_font_family, 11, "bold"), fg="red"); self.status_text_label.pack(side="right", padx=25)
        self.param_frame = tk.LabelFrame(self.left_ui_frame, font=f_normal); self.param_frame.pack(fill="x", padx=10, pady=2)
        slide_sub_frame = tk.Frame(self.param_frame); slide_sub_frame.pack(padx=10, pady=2, fill="x")
        self.p_label = tk.Label(slide_sub_frame, font=f_normal); self.p_label.grid(row=0, column=0, sticky="w", padx=5)
        self.power_value = tk.IntVar(value=200); self.power_slider = tk.Scale(slide_sub_frame, from_=20, to=500, orient="horizontal", variable=self.power_value, length=250, font=f_small, showvalue=False, command=lambda e: self.sync_entry_from_slider('p')); self.power_slider.grid(row=0, column=1, padx=10)
        self.power_entry = tk.Entry(slide_sub_frame, width=6, font=f_bold, justify="center"); self.power_entry.grid(row=0, column=2, padx=5); self.power_entry.insert(0, "200"); self.power_entry.bind("<Return>", lambda e: self.sync_slider_from_entry('p'))
        self.t_label = tk.Label(slide_sub_frame, font=f_normal); self.t_label.grid(row=1, column=0, sticky="w", padx=5)
        self.time_value = tk.IntVar(value=1000); self.time_slider = tk.Scale(slide_sub_frame, from_=100, to=10000, resolution=100, orient="horizontal", variable=self.time_value, length=250, font=f_small, showvalue=False, command=lambda e: self.sync_entry_from_slider('t')); self.time_slider.grid(row=1, column=1, padx=10)
        self.time_entry = tk.Entry(slide_sub_frame, width=6, font=f_bold, justify="center"); self.time_entry.grid(row=1, column=2, padx=5); self.time_entry.insert(0, "1000"); self.time_entry.bind("<Return>", lambda e: self.sync_slider_from_entry('t'))
        self.main_ctrl_frame = tk.Frame(self.left_ui_frame); self.main_ctrl_frame.pack(padx=10, pady=2, fill="x")
        self.sys_group = tk.LabelFrame(self.main_ctrl_frame, font=f_small_bold); self.sys_group.pack(fill="x", pady=5)
        sys_inner = tk.Frame(self.sys_group); sys_inner.pack(anchor="center"); self.create_sys_buttons(sys_inner, f_small_bold)
        self.mode2_group = tk.LabelFrame(self.main_ctrl_frame, font=f_small_bold, fg="blue"); self.mode2_group.pack(fill="x", padx=5, pady=5)
        lever_container = tk.Frame(self.mode2_group); lever_container.pack(anchor="center", pady=5); self.create_lever_buttons(lever_container, f_small, f_small_bold)
        self.func_group = tk.LabelFrame(self.main_ctrl_frame, font=f_small_bold); self.func_group.pack(fill="x", pady=5)
        func_inner = tk.Frame(self.func_group); func_inner.pack(anchor="center"); self.create_func_buttons(func_inner, f_small_bold)
        self.log_frame = tk.LabelFrame(self.left_ui_frame, font=f_normal); self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_display = scrolledtext.ScrolledText(self.log_frame, height=10, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4"); self.log_display.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_display.tag_config("send", foreground="#61afef"); self.log_display.tag_config("ok", foreground="#98c379"); self.log_display.tag_config("error", foreground="#e06c75"); self.log_display.tag_config("welcome", foreground="#FFD700", font=("Consolas", 10, "bold"))
        self.right_que_frame = tk.LabelFrame(self.root, font=f_bold, fg="blue"); self.right_que_frame.pack(side="right", fill="both", padx=10, pady=5); self.right_que_frame.configure(width=500); self.right_que_frame.pack_propagate(False)
        mode_btn_frame = tk.Frame(self.right_que_frame); mode_btn_frame.pack(fill="x", padx=5, pady=5)
        self.mode_inst_btn = tk.Button(mode_btn_frame, font=f_small_bold, height=4, bg="#90EE90", relief="sunken", command=lambda: self.set_exec_mode(True)); self.mode_inst_btn.pack(side="left", expand=True, fill="x")
        self.mode_que_btn = tk.Button(mode_btn_frame, font=f_small_bold, height=4, bg="#f0f0f0", relief="raised", command=lambda: self.set_exec_mode(False)); self.mode_que_btn.pack(side="left", expand=True, fill="x")
        self.que_listbox = tk.Listbox(self.right_que_frame, font=("Consolas", 11), bg="#f8f9fa", selectbackground="#FFD700", selectforeground="black", activestyle='none'); self.que_listbox.pack(fill="both", expand=True, padx=5, pady=2); self.que_listbox.bind("<Double-1>", self.delete_que_item) 
        self.timer_label = tk.Label(self.right_que_frame, text="READY", font=self.f_timer, fg="#D32F2F", bg="#ffffff", relief="sunken", bd=5, height=2); self.timer_label.pack(fill="x", padx=5, pady=10)
        self.run_que_btn = tk.Button(self.right_que_frame, bg="#98c379", font=f_bold, height=2, command=self.handle_run_stop_click); self.run_que_btn.pack(fill="x", padx=5, pady=2)
        self.clear_que_btn = tk.Button(self.right_que_frame, font=f_small, command=self.clear_queue); self.clear_que_btn.pack(fill="x", padx=5, pady=2)

    def sync_entry_from_slider(self, target):
        if target == 'p': self.power_entry.delete(0, tk.END); self.power_entry.insert(0, str(self.power_value.get()))
        else: self.time_entry.delete(0, tk.END); self.time_entry.insert(0, str(self.time_value.get()))

    def sync_slider_from_entry(self, target):
        try:
            if target == 'p': val = int(self.power_entry.get()); val = max(20, min(500, val)); self.power_value.set(val); self.sync_entry_from_slider('p')
            else: val = int(self.time_entry.get()); val = max(100, min(10000, val)); self.time_value.set(val); self.sync_entry_from_slider('t')
            self.root.focus()
        except: self.sync_entry_from_slider(target)

    def update_timer_to_mode_name(self):
        if self.immediate_mode and not self.is_moving:
            d = self.languages[self.current_lang]; self.timer_label.config(text=d["mode_label_inst"], fg="#1976D2") 

    def show_speed_temporarily(self):
        if not self.immediate_mode: return
        d = self.languages[self.current_lang]; speed_text = d["speed_disp"].format(self.speed_step)
        self.timer_label.config(text=speed_text, fg="#EF6C00") 
        if self.speed_display_timer: self.root.after_cancel(self.speed_display_timer)
        self.speed_display_timer = self.root.after(2000, self.update_timer_to_mode_name)

    def delete_que_item(self, event):
        if self.execution_active: return 
        selection = self.que_listbox.curselection()
        if selection:
            index = selection[0]; self.que_listbox.delete(index) 
            if index < len(self.cmd_queue): del self.cmd_queue[index] 
            self.refresh_que_list_display()

    def refresh_que_list_display(self):
        temp_queue = self.cmd_queue.copy(); self.que_listbox.delete(0, tk.END); self.que_count = 1
        for item in temp_queue:
            cmd, wait, desc = item['cmd'], item['wait'], item['desc']
            if "speed" in cmd: log_desc = f"{self.que_count}. {desc}"
            elif cmd == "INTERNAL_DELAY": log_desc = f"{self.que_count}. {desc} ({int(wait*1000)}ms)"
            elif any(x in cmd for x in ["up", "down", "forward", "back", "left", "right", "ccw", "cw"]):
                parts = cmd.split(); p, t = parts[1], parts[2]; log_desc = f"{self.que_count}. {desc} ({p}, {t}ms)"
            else: log_desc = f"{self.que_count}. {desc}"
            self.que_listbox.insert(tk.END, log_desc); self.que_count += 1

    def handle_run_stop_click(self):
        if self.execution_active: self.execution_active = False; self.log("Stop", "error"); self.reset_run_button_ui(completed=False)
        else: self.start_queue_execution()

    def start_queue_execution(self):
        if not self.ser or not self.cmd_queue: return
        d = self.languages[self.current_lang]; self.que_listbox.selection_clear(0, tk.END); self.execution_active = True; self.run_que_btn.config(text=d["stop_que"], bg="#e06c75", fg="white"); self.clear_que_btn.config(state="disabled"); self.update_button_states(False)
        threading.Thread(target=self.queue_worker_thread, daemon=True).start()

    def queue_worker_thread(self):
        d = self.languages[self.current_lang]
        for idx, item in enumerate(self.cmd_queue):
            if not self.execution_active: break
            self.root.after(0, lambda i=idx: self.highlight_que_item(i))
            cmd, wait, desc = item['cmd'], item['wait'], item['desc']
            try:
                if cmd == "INTERNAL_DELAY": self.countdown_wait_ms(wait, desc)
                elif self.ser and self.ser.is_open:
                    self.root.after(0, lambda c=cmd: self.log(f"{d['send']}: {c}", "send"))
                    self.ser.write((cmd + '\r').encode()); self.countdown_wait_ms(wait, desc) 
                    if self.execution_active:
                        self.root.after(0, lambda: self.timer_label.config(text=d["tm_wait_rx"], fg="orange"))
                        if self.ser.readable():
                            res = self.ser.readline().decode().strip()
                            if res: self.root.after(0, lambda r=res: self.log(f"{d['recv']}: {r}", "ok"))
                            self.root.after(0, lambda: self.timer_label.config(text=d["tm_stable"], fg="purple"))
                            for _ in range(60): 
                                if not self.execution_active: break
                                time.sleep(0.05)
            except Exception as e: self.root.after(0, lambda err=e: self.log(f"ERROR: {str(err)}", "error"))
            self.root.after(0, lambda i=idx: self.unhighlight_que_item(i))
        was_interrupted = not self.execution_active; self.execution_active = False; self.root.after(0, lambda: self.reset_run_button_ui(completed=not was_interrupted))

    def countdown_wait_ms(self, seconds, label_text, show_counter=True):
        remaining_ms = int(seconds * 1000)
        while remaining_ms >= 0 and (self.execution_active or self.is_moving):
            if show_counter:
                display_num = f"{remaining_ms}ms"; self.root.after(0, lambda n=display_num: self.timer_label.config(text=n, fg="blue"))
            if remaining_ms <= 0: break
            time.sleep(0.05); remaining_ms -= 50

    def highlight_que_item(self, index): self.que_listbox.itemconfig(index, bg="#FFD700"); self.que_listbox.see(index)
    def unhighlight_que_item(self, index): self.que_listbox.itemconfig(index, bg="#f8f9fa")

    def send_command(self, action, is_move, delay):
        if not self.ser: return
        if self.immediate_mode:
            if self.is_moving and action != "emergency": return
            if time.time() - self.last_click_time < 0.2: return
            self.last_click_time = time.time()
        d = self.languages[self.current_lang]; p = self.power_value.get(); t = self.time_value.get(); btn_disp = d.get(action, action.upper()).replace("\n", " "); show_timer = False
        if action == "hover": cmd = "INTERNAL_DELAY"; wait = t / 1000.0; log_desc = f"{btn_disp} ({t}ms)"; show_timer = True
        elif is_move:
            if action == "up": p = int(p * 0.6)
            cmd = f"{action} {p} {t}"; wait = (t / 1000.0); log_desc = f"{btn_disp} ({p}, {t}ms)"; show_timer = True
        elif action in ["start", "stop"]: cmd = action; wait = 0.5; log_desc = f"{btn_disp}"; show_timer = False 
        elif "speed" in action: cmd = action; wait = 0.5; log_desc = f"{btn_disp}"; show_timer = False 
        elif action == "mapping_start": cmd = action; wait = 3.0; log_desc = f"{btn_disp}"; show_timer = False 
        elif action in ["headless", "battery?", "funled", "gyroreset"]: cmd = action; wait = 1.0; log_desc = f"{btn_disp}"; show_timer = False 
        else: cmd = action; wait = 7.0 if action == "takeoff" else max(1.5, delay); log_desc = f"{btn_disp}"; show_timer = (action in ["takeoff", "land"])
        if self.immediate_mode:
            if self.speed_display_timer: self.root.after_cancel(self.speed_display_timer); self.speed_display_timer = None
            self.is_moving = True; self.update_button_states(False); self.log(f"{d['send']}: {cmd}", "send")
            threading.Thread(target=self._do_send_async, args=(cmd, wait, show_timer), daemon=True).start()
        else:
            selection = self.que_listbox.curselection(); new_item = {'cmd': cmd, 'wait': wait, 'desc': btn_disp}
            if selection:
                idx = selection[0] + 1; self.cmd_queue.insert(idx, new_item); self.refresh_que_list_display(); self.que_listbox.selection_clear(0, tk.END); self.que_listbox.selection_set(idx); self.que_listbox.see(idx)
            else: self.cmd_queue.append(new_item); self.que_listbox.insert(tk.END, f"{self.que_count}. {log_desc}"); self.que_count += 1
            self.timer_label.config(text=d["tm_ready"], fg="#D32F2F")

    def _do_send_async(self, cmd, wait, show_timer):
        d = self.languages[self.current_lang]
        try:
            if cmd == "INTERNAL_DELAY": self.countdown_wait_ms(wait, "WAIT", show_timer)
            else:
                self.ser.write((cmd + '\r').encode()); self.countdown_wait_ms(wait, "PROC", show_timer)
                if self.ser.readable():
                    res = self.ser.readline().decode().strip()
                    if res: self.root.after(0, lambda r=res: self.log(f"{d['recv']}: {r}", "ok"))
        except Exception as e: self.root.after(0, lambda err=e: self.log(f"ERROR: {str(err)}", "error"))
        finally:
            self.is_moving = False; self.root.after(0, lambda: self.update_button_states(True))
            if self.immediate_mode: self.root.after(0, self.update_timer_to_mode_name) 

    def set_exec_mode(self, is_immediate):
        self.immediate_mode = is_immediate; d = self.languages[self.current_lang]
        if is_immediate: self.mode_inst_btn.config(bg="#90EE90", relief="sunken"); self.mode_que_btn.config(bg="#f0f0f0", relief="raised"); self.run_que_btn.config(state="disabled"); self.update_timer_to_mode_name() 
        else: self.mode_que_btn.config(bg="#90EE90", relief="sunken"); self.mode_inst_btn.config(bg="#f0f0f0", relief="raised"); self.run_que_btn.config(state="normal" if self.ser else "disabled"); self.timer_label.config(text=d["tm_ready"], fg="#D32F2F")

    def reset_run_button_ui(self, completed=False):
        d = self.languages[self.current_lang]; self.run_que_btn.config(bg="#98c379", fg="black", state="normal", text=d["run_que"]); self.clear_que_btn.config(state="normal") 
        if completed: self.timer_label.config(text=d["tm_done"], fg="#2E7D32")
        elif not self.immediate_mode: self.timer_label.config(text=d["tm_ready"], fg="#D32F2F")
        elif self.immediate_mode: self.update_timer_to_mode_name()
        self.update_button_states(True)

    def clear_queue(self):
        if self.execution_active: return 
        d = self.languages[self.current_lang]; self.que_listbox.delete(0, tk.END); self.cmd_queue = []; self.que_count = 1
        if not self.immediate_mode: self.timer_label.config(text=d["tm_ready"], fg="#D32F2F")
        else: self.update_timer_to_mode_name()

    def toggle_serial(self):
        if self.ser: 
            self.ser.close(); self.ser = None; self.update_button_states(False); self.port_entry.config(state="normal"); self.conn_btn.config(bg="lightblue"); self.refresh_btn.config(state="normal"); self.change_lang(self.current_lang)
        else:
            try:
                self.ser = serial.Serial(port=self.port_entry.get(), baudrate=9600, timeout=1); self.update_button_states(True); self.port_entry.config(state="disabled"); self.conn_btn.config(bg="lightpink"); self.refresh_btn.config(state="disabled"); self.change_lang(self.current_lang); self.log("SYUBEA Corporation", "welcome"); self.log("www.1510.co.kr", "welcome"); self.log(f"{self.version}", "welcome")
            except: messagebox.showerror("Error", "Connect Failed")

    def update_button_states(self, enabled):
        st = "normal" if enabled else "disabled"
        for b in self.buttons: b.config(state=st)
        if self.emergency_btn: self.emergency_btn.config(state="normal")
        self.power_slider.config(state=st); self.time_slider.config(state=st); self.power_entry.config(state=st); self.time_entry.config(state=st)
        if not self.execution_active and not self.is_moving: 
            self.run_que_btn.config(state="normal" if self.ser and not self.immediate_mode else "disabled"); self.clear_que_btn.config(state="normal" if not self.immediate_mode else "disabled")

    def create_sys_buttons(self, parent, font):
        self.btn_mapping = []
        self.emergency_btn = tk.Button(parent, bg="red", fg="white", width=12, height=2, font=font, command=self.send_emergency); self.emergency_btn.pack(side="left", padx=8, pady=5); self.btn_mapping.append((self.emergency_btn, "emergency"))
        btns_sys = [("start", "start", 0.5), ("off", "stop", 0.5), ("takeoff", "takeoff", 1.5), ("land", "land", 1.5)]
        for act, key, dly in btns_sys:
            bg = "lightgreen" if act=="takeoff" else "orange" if act=="land" else None
            b = self.create_custom_button(parent, act, is_move=False, delay=dly, bg=bg, height=2, width=12, font=font); b.pack(side="left", padx=8, pady=5); self.btn_mapping.append((b, key))

    def create_lever_buttons(self, parent, f_small, f_small_bold):
        for i in range(2):
            frame = tk.LabelFrame(parent, font=f_small_bold); frame.pack(side="left", padx=25, pady=5)
            if i == 0:
                self.left_group = frame; actions = [("up", "up", 0, 1), ("ccw", "ccw", 1, 0), ("cw", "cw", 1, 2), ("down", "down", 2, 1)]
                for act, key, r, c in actions: b = self.create_custom_button(frame, act, is_move=True, width=11, height=2, font=f_small); b.grid(row=r, column=c, padx=4, pady=4); self.btn_mapping.append((b, key))
                self.speed_btn = tk.Button(frame, bg="#e3f2fd", width=7, height=2, font=(self.default_font_family, 8, "bold"), command=self.toggle_speed, relief="raised", bd=3); self.speed_btn.grid(row=1, column=1, padx=4, pady=4); self.btn_mapping.append((self.speed_btn, "speed")); self.buttons.append(self.speed_btn)
            else:
                self.right_group = frame; actions = [("forward", "forward", 0, 1), ("left", "left", 1, 0), ("right", "right", 1, 2), ("back", "back", 2, 1)]
                for act, key, r, c in actions: b = self.create_custom_button(frame, act, is_move=True, width=11, height=2, font=f_small); b.grid(row=r, column=c, padx=4, pady=4); self.btn_mapping.append((b, key))
                self.hover_btn = tk.Button(frame, bg="#fff9c4", width=7, height=2, font=(self.default_font_family, 8, "bold"), command=lambda: self.send_command("hover", False, 0.5), relief="raised", bd=3); self.hover_btn.grid(row=1, column=1, padx=4, pady=4); self.btn_mapping.append((self.hover_btn, "hover")); self.buttons.append(self.hover_btn)

    def create_func_buttons(self, parent, font):
        funcs = [("headless", "headless", "lavender", 0.5), ("battery?", "battery", None, 0.5), ("funled", "led", "lightcyan", 0.5), ("gyroreset", "gyro", None, 0.5), ("mapping_start", "bind", "lightyellow", 3.0)]
        for act, key, bg, dly in funcs:
            b = self.create_custom_button(parent, act, is_move=False, bg=bg, width=12, height=2, delay=dly, font=font); b.pack(side="left", padx=5, pady=5); self.btn_mapping.append((b, key))

    def send_emergency(self):
        if self.ser: self.ser.write(b'emergency\r'); self.log("EMERGENCY (Space)", "error"); self.execution_active = False; self.is_moving = False; self.root.after(0, lambda: self.update_button_states(True))

    def toggle_speed(self):
        self.speed_step = self.speed_step + 1 if self.speed_step < 3 else 1; self.change_lang(self.current_lang); self.send_command(f"speed {self.speed_step}", False, 0.5); self.show_speed_temporarily() 

    def find_ch340_port(self):
        for p in serial.tools.list_ports.comports():
            if 'CH340' in p.description.upper() or 'SERIAL' in p.description.upper(): return p.device
        return None

    def refresh_port(self): 
        if self.ser: return 
        self.port_entry.delete(0, tk.END); p = self.find_ch340_port(); self.port_entry.insert(0, p if p else "COM3")

    def create_custom_button(self, parent, action, is_move=False, delay=0.5, bg=None, fg=None, width=10, height=2, font=None):
        btn = tk.Button(parent, width=width, height=height, bg=bg, fg=fg, font=font, command=lambda: self.send_command(action, is_move, delay)); self.buttons.append(btn); return btn

    def change_lang(self, lang_code):
        self.current_lang = lang_code; d = self.languages[lang_code]; self.conn_frame.config(text=d["port_cfg"]); self.conn_btn.config(text=d["disconnect"] if self.ser else d["connect"]); self.refresh_btn.config(text=d["refresh"]); self.update_status_label(); self.param_frame.config(text=d["param_cfg"]); self.p_label.config(text=d["power"]); self.t_label.config(text=d["time"]); self.log_frame.config(text=d["status_title"]); self.sys_group.config(text=d["sys_ctrl"]); self.mode2_group.config(text=d["mode2"]); self.left_group.config(text=d["left_lever"]); self.right_group.config(text=d["right_lever"]); self.func_group.config(text=d["func"]); self.mode_inst_btn.config(text=d["mode_inst"]); self.mode_que_btn.config(text=d["mode_que"]); self.right_que_frame.config(text=d["que_title"]); self.run_que_btn.config(text=d["stop_que"] if self.execution_active else d["run_que"]); self.clear_que_btn.config(text=d["clear_que"])
        if not self.execution_active and not self.is_moving: 
            if not self.immediate_mode: self.timer_label.config(text=d["tm_ready"], fg="#D32F2F")
            else: self.update_timer_to_mode_name()
        for btn, key in self.btn_mapping:
            if key == "speed": btn.config(text=f"{d[key]}\n{self.speed_step}")
            elif key == "hover": btn.config(text=d[key])
            elif key in d: btn.config(text=d[key])

    def log(self, message, tag="system"):
        now = datetime.now().strftime("%H:%M:%S"); self.log_display.insert(tk.END, f"[{now}] {message}\n", tag); self.log_display.see(tk.END)

    def update_status_label(self):
        d = self.languages[self.current_lang]; self.status_text_label.config(text=d['st_connected'] if self.ser else d['st_waiting'], fg="#2E7D32" if self.ser else "#D32F2F")

    def setup_menu(self):
        self.menu_bar = tk.Menu(self.root); self.lang_menu = tk.Menu(self.menu_bar, tearoff=0)
        langs = [("한국어", "KO"), ("English", "EN"), ("中文", "ZH"), ("日本語", "JA"), ("Tiếng Việt", "VI")]
        for name, code in langs: self.lang_menu.add_command(label=name, command=lambda c=code: self.change_lang(c))
        self.menu_bar.add_cascade(label="Language", menu=self.lang_menu); self.menu_bar.add_command(label="syubea.com", command=lambda: webbrowser.open("http://syubea.com")); self.root.config(menu=self.menu_bar)

if __name__ == "__main__":
    root = tk.Tk(); app = DroneController(root); root.mainloop()