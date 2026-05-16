import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial.tools.list_ports
import threading
import time
import toml
import os
import ctypes
import platform
import sv_ttk
import pywinstyles
from swicc_core import SwiccController

try:
    if platform.system() == "Windows":
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

I18N = {
    "zh_CN": {
        "title": "SwiCC Advanced Host Controller - Native Edition",
        "port_label": "串行总线端口:",
        "refresh": "刷新端口",
        "connect": "建立连接",
        "disconnect": "断开连接",
        "scale_label": "界面缩放比例:",
        "lang_label": "系统语言 (Language):",
        "status_unconnected": "● 未连接",
        "status_connected": "● 已连接",
        "left_panel": " 左侧物理控制器 (Joy-Con L) ",
        "right_panel": " 右侧物理控制器 (Joy-Con R) ",
        "record_start": "开始实时录制",
        "record_stop": "停止录制",
        "export_toml": "导出 TOML 宏",
        "loop_count": "循环播放次数:",
        "global_interval": "全局帧间隔(ms):",
        "play_macro": "加载并执行宏队列",
        "log_scan_found": "总线扫描完成，发现 {} 个可用串行端口。",
        "log_scan_none": "扫描失败。未发现可用串行端口，请检查物理连线。",
        "log_scale_update": "图形界面全局缩放比例已更新为: {}%",
        "log_scale_fail": "缩放矩阵计算失败: {}",
        "log_port_mount_success": "成功分配并挂载硬件通信接口: {}",
        "log_port_mount_fail": "端口绑定被系统拒绝: {}",
        "log_bus_detached": "硬件总线描述符已安全释放。",
        "log_record_start": "时序状态捕获引擎已进入监听模式。",
        "log_record_end": "捕获终止，已将 {} 个数据状态帧压入堆栈。",
        "log_save_success": "宏配置文件持久化写入完成: {}",
        "log_save_fail": "文件系统I/O异常: {}",
        "log_load_success": "TOML反序列化完成，已将 {} 个重载轮次加入调度队列。",
        "log_load_fail": "未能在目标文件中提取出有效的数据结构。",
        "log_thread_crash": "时序执行子线程抛出异常: {}",
        "log_macro_finish": "自动化指令序列已被完整消费，总线现已恢复空闲状态。",
        "warn_no_port": "通信参数缺失：请先在下拉列表中指定目标串行端口。",
        "warn_no_conn": "连接未建立：执行此操作前必须建立有效的底层串口链路。",
        "import_image": "导入绘图图片",
        "start_image_draw": "进入矢量高速仿真预览",
        "stop_image_draw": "终止自动绘制",
        "log_img_load_success": "图像加载及几何边界拓扑完成，共提取出 {} 条连续矢量轮廓线。",
        "log_img_draw_start": "图像自动化矢量连续绘制流已激活。",
        "log_img_draw_finish": "矢量轮廓动作流实机绘制完毕，总线现已恢复空闲状态。",
        "log_img_draw_cancel": "图像自动绘制已被用户强行终止，总线已安全释放。"
    },
    "en_US": {
        "title": "SwiCC Advanced Host Controller - Native Edition",
        "port_label": "Serial Bus Port:",
        "refresh": "Refresh",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "scale_label": "UI Scaling Ratio:",
        "lang_label": "Language (语言):",
        "status_unconnected": "● Disconnected",
        "status_connected": "● Connected",
        "left_panel": " Left Physical Controller (Joy-Con L) ",
        "right_panel": " Right Physical Controller (Joy-Con R) ",
        "record_start": "Start Recording",
        "record_stop": "Stop Recording",
        "export_toml": "Export TOML",
        "loop_count": "Loop Iterations:",
        "global_interval": "Global Interval (ms):",
        "play_macro": "Load & Execute Macro",
        "log_scan_found": "Bus scan complete. Found {} available ports.",
        "log_scan_none": "Scan failed. No serial ports available.",
        "log_scale_update": "Global UI scaling updated to: {}%",
        "log_scale_fail": "Scaling matrix calculation failed: {}",
        "log_port_mount_success": "Hardware interface mounted successfully: {}",
        "log_port_mount_fail": "Port binding denied by OS: {}",
        "log_bus_detached": "Hardware bus descriptor released safely.",
        "log_record_start": "State capture engine is now listening.",
        "log_record_end": "Capture terminated. {} frames pushed to stack.",
        "log_save_success": "Configuration persistence complete: {}",
        "log_save_fail": "File system I/O exception: {}",
        "log_load_success": "Deserialization complete. {} iterations scheduled.",
        "log_load_fail": "Failed to extract valid structures from target file.",
        "log_thread_crash": "Execution thread threw an exception: {}",
        "log_macro_finish": "Command sequence fully consumed. Bus is idle.",
        "warn_no_port": "Missing parameters: Please specify a port.",
        "warn_no_conn": "Connection error: Must establish serial link first.",
        "import_image": "Import Image",
        "start_image_draw": "Enter Vector High-Speed Preview",
        "stop_image_draw": "Terminate Auto Draw",
        "log_img_load_success": "Image model complete. Found {} continuous contours.",
        "log_img_draw_start": "Image automated vector drawing sequence started.",
        "log_img_draw_finish": "Vector sequence consumed. Bus is idle.",
        "log_img_draw_cancel": "Image drawing forcefully terminated by user. Bus is safe."
    }
}

class DrawingPreviewWindow:
    def __init__(self, parent, commands, confirm_callback):
        self.top = tk.Toplevel(parent)
        self.top.title("矢量轮廓路径 100x 高速仿真推演器")
        self.top.geometry("560x620")
        self.top.resizable(False, False)
        
        self.commands = commands
        self.confirm_callback = confirm_callback
        
        self.canvas = tk.Canvas(self.top, width=512, height=512, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(pady=15)
        
        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(fill="x", side="bottom", pady=15, padx=24)
        
        self.confirm_btn = ttk.Button(btn_frame, text="确认写入实机 (Confirm Vector Draw)", command=self.confirm, state="disabled", style="Accent.TButton")
        self.confirm_btn.pack(side="right", padx=6)
        
        self.cancel_btn = ttk.Button(btn_frame, text="放弃当前序列 (Cancel)", command=self.top.destroy)
        self.cancel_btn.pack(side="right", padx=6)
        
        self.curr_x, self.curr_y = 128, 128
        self.is_pen_down = False
        self.cmd_index = 0
        self.scale = 2
        
        pywinstyles.apply_style(self.top, "mica")
        pywinstyles.change_header_color(self.top, color="#202020")
        self.animate()
        
    def animate(self):
        batch_size = 50
        for _ in range(batch_size):
            if self.cmd_index >= len(self.commands):
                self.confirm_btn.config(state="normal")
                return
            
            cmd = self.commands[self.cmd_index]
            cmd_type = cmd.get("type")
            
            if cmd_type == "pen_down":
                self.is_pen_down = True
            elif cmd_type == "pen_up":
                self.is_pen_down = False
            elif cmd_type == "move":
                dx = cmd.get("dx", 0)
                dy = cmd.get("dy", 0)
                next_x = self.curr_x + dx
                next_y = self.curr_y + dy
                
                if self.is_pen_down:
                    self.canvas.create_line(
                        self.curr_x * self.scale, self.curr_y * self.scale,
                        next_x * self.scale, next_y * self.scale,
                        fill="#4cc9f0", width=2
                    )
                self.curr_x, self.curr_y = next_x, next_y
                
            self.cmd_index += 1
            
        self.top.after(1, self.animate)
        
    def confirm(self):
        self.top.destroy()
        self.confirm_callback()

class SwiccAdvancedHostApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "zh_CN"
        
        self.root.geometry("1450x1050")
        self.root.minsize(1200, 900) 
        self.root.maxsize(3840, 2160)

        self.controller = SwiccController()
        self.is_connected = False
        self.state = [0x00, 0x00, 0x08, 0x80, 0x80, 0x80, 0x80]
        self.is_recording = False
        self.macro_steps = []
        self.current_step_start = 0
        self.last_hex_str = "00000880808080"
        self.base_scaling = self.root.tk.call('tk', 'scaling')
        self.extracted_contours = None
        
        self.drawing_requested_cancel = threading.Event()

        self.setup_ui()
        self.scan_ports()
        self.apply_language_strings()

    def tr(self, key, *args):
        text = I18N.get(self.current_lang, I18N["en_US"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        conn_frame = ttk.Frame(self.root)
        conn_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 15))
        
        for c in range(8):
            conn_frame.columnconfigure(c, weight=0)
        conn_frame.columnconfigure(4, weight=1)

        self.port_label = ttk.Label(conn_frame, text="")
        self.port_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.refresh_btn = ttk.Button(conn_frame, text="", command=self.scan_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        self.connect_btn = ttk.Button(conn_frame, text="", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=10, pady=5)

        ttk.Frame(conn_frame).grid(row=0, column=4, sticky="nsew")

        self.status_label = ttk.Label(conn_frame, text="", font=("Segoe UI", 13, "bold"))
        self.status_label.grid(row=0, column=5, padx=20, pady=5, sticky="e")

        self.scale_label = ttk.Label(conn_frame, text="")
        self.scale_label.grid(row=1, column=0, padx=(0, 5), pady=10, sticky="w")
        
        self.scale_var = tk.StringVar(value="100%")
        self.scale_combo = ttk.Combobox(conn_frame, textvariable=self.scale_var, values=["80%", "100%", "125%", "150%", "175%", "200%"], state="readonly")
        self.scale_combo.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        self.scale_combo.bind("<<ComboboxSelected>>", self.change_scaling)

        self.lang_label = ttk.Label(conn_frame, text="")
        self.lang_label.grid(row=1, column=2, padx=(20, 5), pady=10, sticky="w")

        self.lang_var = tk.StringVar(value="简体中文")
        self.lang_combo = ttk.Combobox(conn_frame, textvariable=self.lang_var, values=["简体中文", "English"], state="readonly")
        self.lang_combo.grid(row=1, column=3, padx=5, pady=10, sticky="ew")
        self.lang_combo.bind("<<ComboboxSelected>>", self.change_language)

        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self.left_panel = ttk.LabelFrame(main_frame, text="", padding=20)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        self.right_panel = ttk.LabelFrame(main_frame, text="", padding=20)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        for i in range(4):
            self.left_panel.columnconfigure(i, weight=1)
            self.right_panel.columnconfigure(i, weight=1)

        self.create_button(self.left_panel, "ZL", 1, 0x40).grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.create_button(self.left_panel, "L", 1, 0x10).grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.create_button(self.left_panel, "Minus (-)", 0, 0x01).grid(row=0, column=2, padx=8, pady=8, sticky="ew")
        self.create_button(self.left_panel, "Capture", 0, 0x20).grid(row=1, column=2, padx=8, pady=8, sticky="ew")
        self.setup_dpad(self.left_panel).grid(row=1, column=0, columnspan=2, pady=25)
        self.setup_joystick(self.left_panel, "L-Stick", 3, 4).grid(row=2, column=0, columnspan=3, pady=25)
        self.create_button(self.left_panel, "L-Click", 0, 0x04).grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")

        self.create_button(self.right_panel, "Plus (+)", 0, 0x02).grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.create_button(self.right_panel, "R", 1, 0x20).grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.create_button(self.right_panel, "ZR", 1, 0x80).grid(row=0, column=2, padx=8, pady=8, sticky="ew")
        self.create_button(self.right_panel, "Home", 0, 0x10).grid(row=1, column=0, padx=8, pady=8, sticky="ew")
        self.setup_abxy(self.right_panel).grid(row=1, column=1, columnspan=2, pady=25)
        self.setup_joystick(self.right_panel, "R-Stick", 5, 6).grid(row=2, column=0, columnspan=3, pady=25)
        self.create_button(self.right_panel, "R-Click", 0, 0x08).grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")

        macro_frame = ttk.Frame(self.root)
        macro_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=15)
        
        for mc in range(7):
            macro_frame.columnconfigure(mc, weight=0)
        macro_frame.columnconfigure(6, weight=1)

        self.record_btn = ttk.Button(macro_frame, text="", command=self.start_recording, style="Accent.TButton")
        self.record_btn.grid(row=0, column=0, padx=(0, 10), pady=5)

        self.stop_btn = ttk.Button(macro_frame, text="", command=self.stop_recording, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5, pady=5)

        self.save_btn = ttk.Button(macro_frame, text="", command=self.save_macro, state="disabled")
        self.save_btn.grid(row=0, column=2, padx=10, pady=5)

        self.loop_label = ttk.Label(macro_frame, text="")
        self.loop_label.grid(row=0, column=3, padx=(20, 5), pady=5, sticky="w")
        
        self.loop_spin = ttk.Spinbox(macro_frame, from_=1, to=9999)
        self.loop_spin.grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        self.loop_spin.set(1)

        self.interval_label = ttk.Label(macro_frame, text="")
        self.interval_label.grid(row=0, column=5, padx=(15, 5), pady=5, sticky="w")
        
        self.interval_entry = ttk.Entry(macro_frame)
        self.interval_entry.grid(row=0, column=6, padx=5, pady=5, sticky="w")
        self.interval_entry.insert(0, "0")

        self.play_btn = ttk.Button(macro_frame, text="", command=self.load_and_play_macro, style="Accent.TButton")
        self.play_btn.grid(row=0, column=7, padx=(10, 0), pady=5, sticky="e")

        image_draw_frame = ttk.Frame(self.root)
        image_draw_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=15)

        self.import_img_btn = ttk.Button(image_draw_frame, text="", command=self.import_image_file, style="Accent.TButton")
        self.import_img_btn.grid(row=0, column=0, padx=(0, 10), pady=5)

        self.draw_img_btn = ttk.Button(image_draw_frame, text="", command=self.start_vector_drawing_plan, state="disabled")
        self.draw_img_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.stop_draw_btn = ttk.Button(image_draw_frame, text="", command=self.stop_image_drawing_execution, state="disabled")
        self.stop_draw_btn.grid(row=0, column=2, padx=10, pady=5)

        self.log_text = tk.Text(self.root, height=6, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 14), relief="flat")
        self.log_text.grid(row=4, column=0, sticky="ew", padx=30, pady=(0, 30))
        self.log_text.config(state="disabled")

    def apply_language_strings(self):
        self.root.title(self.tr("title"))
        self.port_label.config(text=self.tr("port_label"))
        self.refresh_btn.config(text=self.tr("refresh"))
        if self.is_connected:
            self.connect_btn.config(text=self.tr("disconnect"))
            self.status_label.config(text=self.tr("status_connected"), foreground="#4cc9f0")
        else:
            self.connect_btn.config(text=self.tr("connect"))
            self.status_label.config(text=self.tr("status_unconnected"), foreground="#ff6b6b")
            
        self.scale_label.config(text=self.tr("scale_label"))
        self.lang_label.config(text=self.tr("lang_label"))
        self.left_panel.config(text=self.tr("left_panel"))
        self.right_panel.config(text=self.tr("right_panel"))
        self.record_btn.config(text=self.tr("record_start"))
        self.stop_btn.config(text=self.tr("record_stop"))
        self.save_btn.config(text=self.tr("export_toml"))
        self.loop_label.config(text=self.tr("loop_count"))
        self.interval_label.config(text=self.tr("global_interval"))
        self.play_btn.config(text=self.tr("play_macro"))
        self.import_img_btn.config(text=self.tr("import_image"))
        self.draw_img_btn.config(text=self.tr("start_image_draw"))
        self.stop_draw_btn.config(text=self.tr("stop_image_draw"))

    def change_language(self, event=None):
        selected = self.lang_var.get()
        self.current_lang = "en_US" if selected == "English" else "zh_CN"
        self.apply_language_strings()

    def scan_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.set(port_list[0])
            self.log(self.tr("log_scan_found", len(port_list)))
        else:
            self.port_combo.set("")
            self.log(self.tr("log_scan_none"))

    def change_scaling(self, event=None):
        scale_str = self.scale_var.get().replace("%", "")
        try:
            percentage = int(scale_str) / 100.0
            new_factor = self.base_scaling * percentage
            self.root.tk.call('tk', 'scaling', new_factor)
            
            style = ttk.Style()
            dynamic_size = int(12 * percentage)
            style.configure(".", font=("Segoe UI", dynamic_size))
            style.configure("TButton", font=("Segoe UI", dynamic_size))
            style.configure("Accent.TButton", font=("Segoe UI", dynamic_size, "bold"))
            style.configure("TLabelframe.Label", font=("Segoe UI", int(13 * percentage), "bold"))
            
            self.log(self.tr("log_scale_update", scale_str))
        except Exception as e:
            err_msg = str(e)
            self.log(self.tr("log_scale_fail", err_msg))

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def toggle_connection(self):
        if self.is_connected: self.close_serial()
        else: self.open_serial()

    def open_serial(self):
        port = self.port_combo.get().strip()
        if not port:
            messagebox.showwarning("Warning", self.tr("warn_no_port"))
            return
            
        if self.controller.connect(port):
            self.is_connected = True
            self.connect_btn.config(text=self.tr("disconnect"))
            self.status_label.config(text=self.tr("status_connected"), foreground="#4cc9f0")
            self.log(self.tr("log_port_mount_success", port))
            self.send_update()
        else:
            messagebox.showerror("Error", self.tr("log_port_mount_fail", "端口绑定被系统拒绝或不可用"))

    def close_serial(self):
        self.controller.disconnect()
        self.is_connected = False
        self.connect_btn.config(text=self.tr("connect"))
        self.status_label.config(text=self.tr("status_unconnected"), foreground="#ff6b6b")
        self.log(self.tr("log_bus_detached"))

    def generate_hex_state(self):
        return f"{self.state[0]:02X}{self.state[1]:02X}{self.state[2]:02X}{self.state[3]:02X}{self.state[4]:02X}{self.state[5]:02X}{self.state[6]:02X}"

    def send_update(self):
        hex_str = self.generate_hex_state()
        if self.is_connected:
            self.controller.send_hex_state_str(hex_str)

        if self.is_recording:
            now = time.time()
            if hex_str != self.last_hex_str:
                duration_ms = int((now - self.current_step_start) * 1000)
                if duration_ms > 0:
                    self.macro_steps.append({"state": self.last_hex_str, "duration": duration_ms, "interval": 0})
                self.current_step_start = now
                self.last_hex_str = hex_str

    def create_button(self, parent, text, byte_idx, bit_mask):
        btn = ttk.Button(parent, text=text)
        btn.bind('<ButtonPress-1>', lambda e: self.btn_press(byte_idx, bit_mask))
        btn.bind('<ButtonRelease-1>', lambda e: self.btn_release(byte_idx, bit_mask))
        return btn

    def btn_press(self, byte_idx, bit_mask):
        self.state[byte_idx] |= bit_mask
        self.send_update()

    def btn_release(self, byte_idx, bit_mask):
        self.state[byte_idx] &= ~bit_mask
        self.send_update()

    def setup_dpad(self, parent):
        frame = ttk.Frame(parent)
        btn_up = ttk.Button(frame, text="UP")
        btn_down = ttk.Button(frame, text="DOWN")
        btn_left = ttk.Button(frame, text="LEFT")
        btn_right = ttk.Button(frame, text="RIGHT")

        btn_up.bind('<ButtonPress-1>', lambda e: self.dpad_press(0x00))
        btn_down.bind('<ButtonPress-1>', lambda e: self.dpad_press(0x04))
        btn_left.bind('<ButtonPress-1>', lambda e: self.dpad_press(0x06))
        btn_right.bind('<ButtonPress-1>', lambda e: self.dpad_press(0x02))

        for btn in [btn_up, btn_down, btn_left, btn_right]:
            btn.bind('<ButtonRelease-1>', lambda e: self.dpad_press(0x08))

        btn_up.grid(row=0, column=1, padx=4, pady=4)
        btn_left.grid(row=1, column=0, padx=4, pady=4)
        btn_right.grid(row=1, column=2, padx=4, pady=4)
        btn_down.grid(row=2, column=1, padx=4, pady=4)
        return frame

    def dpad_press(self, val):
        self.state[2] = val
        self.send_update()

    def setup_abxy(self, parent):
        frame = ttk.Frame(parent)
        self.create_button(frame, "X", 1, 0x08).grid(row=0, column=1, padx=4, pady=4)
        self.create_button(frame, "Y", 1, 0x01).grid(row=1, column=0, padx=4, pady=4)
        self.create_button(frame, "A", 1, 0x04).grid(row=1, column=2, padx=4, pady=4)
        self.create_button(frame, "B", 1, 0x02).grid(row=2, column=1, padx=4, pady=4)
        return frame

    def setup_joystick(self, parent, label_text, x_byte_idx, y_byte_idx):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text=label_text, font=("Segoe UI", 13, "bold")).pack(pady=(0, 10))
        canvas_size = 180
        center = canvas_size // 2
        
        canvas = tk.Canvas(frame, width=canvas_size, height=canvas_size, bg="#2d2d2d", relief="flat", highlightthickness=1, highlightbackground="#555")
        canvas.pack()
        
        canvas.create_oval(20, 20, canvas_size-20, canvas_size-20, outline="#666", width=2)
        canvas.create_line(center, 20, center, canvas_size-20, fill="#555", dash=(2, 2))
        canvas.create_line(20, center, canvas_size-20, center, fill="#555", dash=(2, 2))
        dot = canvas.create_oval(center-18, center-18, center+18, center+18, fill="#0078D4", outline="")

        def on_drag(event):
            x = max(0, min(canvas_size, event.x))
            y = max(0, min(canvas_size, event.y))
            canvas.coords(dot, x-18, y-18, x+18, y+18)
            self.state[x_byte_idx] = int((x / canvas_size) * 255)
            self.state[y_byte_idx] = int((y / canvas_size) * 255)
            self.send_update()

        def on_release(event):
            canvas.coords(dot, center-18, center-18, center+18, center+18)
            self.state[x_byte_idx] = 0x80
            self.state[y_byte_idx] = 0x80
            self.send_update()

        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        return frame

    def start_recording(self):
        self.macro_steps = []
        self.is_recording = True
        self.current_step_start = time.time()
        self.last_hex_str = self.generate_hex_state()
        
        self.record_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.save_btn.config(state="disabled")
        self.log(self.tr("log_record_start"))

    def stop_recording(self):
        self.is_recording = False
        now = time.time()
        duration_ms = int((now - self.current_step_start) * 1000)
        if duration_ms > 0:
            self.macro_steps.append({"state": self.last_hex_str, "duration": duration_ms, "interval": 0})
            
        self.record_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.save_btn.config(state="normal" if len(self.macro_steps) > 0 else "disabled")
        self.log(self.tr("log_record_end", len(self.macro_steps)))

    def save_macro(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".toml", filetypes=[("TOML", "*.toml")])
        if file_path:
            try:
                loop_count = int(self.loop_spin.get())
                with open(file_path, "w", encoding="utf-8") as f:
                    toml.dump({"loop": loop_count, "step": self.macro_steps}, f)
                self.log(self.tr("log_save_success", os.path.basename(file_path)))
            except Exception as e:
                err_msg = str(e)
                messagebox.showerror("Error", self.tr("log_save_fail", err_msg))

    def load_and_play_macro(self):
        if not self.is_connected:
            messagebox.showwarning("Warning", self.tr("warn_no_conn"))
            return

        file_path = filedialog.askopenfilename(filetypes=[("TOML", "*.toml")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f: data = toml.load(f)
                steps = data.get("step", [])
                loop_count = data.get("loop", int(self.loop_spin.get()))
                if not steps: raise ValueError("Data Structure Error")
                
                try: global_interval = int(self.interval_entry.get())
                except: global_interval = 0

                self.log(self.tr("log_load_success", loop_count))
                threading.Thread(target=self.execute_advanced_playback, args=(steps, loop_count, global_interval), daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", self.tr("log_load_fail"))

    def execute_advanced_playback(self, steps, loop_count, global_interval):
        self.root.after(0, lambda: self.play_btn.config(state="disabled"))
        self.root.after(0, lambda: self.record_btn.config(state="disabled"))
        try:
            for iteration in range(loop_count):
                for step in steps:
                    self.controller.send_hex_state_str(step.get('state', '00000880808080'))
                    time.sleep(step.get("duration", 100) / 1000.0)
                    self.controller.send_hex_state_str("00000880808080")
                    
                    total_sleep = step.get("interval", 0) + global_interval
                    if total_sleep > 0: time.sleep(total_sleep / 1000.0)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.log(self.tr("log_thread_crash", msg)))
        finally:
            self.controller.send_hex_state_str("00000880808080")
            self.root.after(0, lambda: self.log(self.tr("log_macro_finish")))
            self.root.after(0, lambda: self.play_btn.config(state="normal"))
            self.root.after(0, lambda: self.record_btn.config(state="normal"))

    def import_image_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.svg")])
        if file_path:
            try:
                from image_processor import extract_vector_contours
                self.extracted_contours = extract_vector_contours(file_path)
                self.log(self.tr("log_img_load_success", len(self.extracted_contours)))
                self.draw_img_btn.config(state="normal")
            except Exception as e:
                err_msg = str(e)
                messagebox.showerror("Error", f"图像矢量解析失败: {err_msg}")

    def start_vector_drawing_plan(self):
        if not self.extracted_contours:
            return
            
        try:
            from path_planner import plan_vector_drawing_commands
            all_commands = plan_vector_drawing_commands(self.extracted_contours, (128, 128))
            
            if all_commands:
                try:
                    press_ms = 45
                    delay_ms = int(self.interval_entry.get())
                    if delay_ms <= 0:
                        delay_ms = 35
                except:
                    press_ms = 45
                    delay_ms = 35
                    
                DrawingPreviewWindow(
                    self.root, 
                    all_commands, 
                    lambda: self.launch_hardware_vector_drawing(all_commands, press_ms, delay_ms)
                )
        except Exception as e:
            err_msg = str(e)
            messagebox.showerror("Error", f"生成矢量路径规划失败: {err_msg}")

    def launch_hardware_vector_drawing(self, commands, press_ms, delay_ms):
        self.drawing_requested_cancel.clear()
        self.import_img_btn.config(state="disabled")
        self.draw_img_btn.config(state="disabled")
        self.stop_draw_btn.config(state="normal")
        
        threading.Thread(
            target=self.execute_vector_hardware_draw, 
            args=(commands, press_ms, delay_ms), 
            daemon=True
        ).start()

    def stop_image_drawing_execution(self):
        self.drawing_requested_cancel.set()
        self.stop_draw_btn.config(state="disabled")

    def execute_vector_hardware_draw(self, commands, press_ms, delay_ms):
        try:
            self.root.after(0, lambda: self.log("正在执行绝对硬件坐标回中校准..."))
            
            # 正确配置全局屏幕几何中心回中参数：
            # 屏幕中心偏移 = 640px (X轴) / 360px (Y轴)
            # 设定物理映射率: 1步 = 2px，故步数为 320 与 180
            self.controller.calibrate_center(
                steps_x=320, 
                steps_y=180, 
                overdrive=750, 
                press_ms=press_ms, 
                delay_ms=delay_ms, 
                cancel_event=self.drawing_requested_cancel
            )
            
            self.root.after(0, lambda: self.log("坐标原点校准完成，开始执行连续矢量轮廓线扫描。"))
            self.root.after(0, lambda: self.log(self.tr("log_img_draw_start")))
            
            self.controller.execute_vector_commands(
                commands=commands, 
                press_ms=press_ms, 
                delay_ms=delay_ms, 
                cancel_event=self.drawing_requested_cancel
            )
            
            self.root.after(0, lambda: self.log(self.tr("log_img_draw_finish")))
        except InterruptedError:
            self.root.after(0, lambda: self.log(self.tr("log_img_draw_cancel")))
        except Exception as e:
            err_str = str(e)
            self.root.after(0, lambda msg=err_str: self.log(f"矢量绘图线程异常: {msg}"))
        finally:
            self.controller.send_hex_state_str("00000880808080")
            self.root.after(0, lambda: self.import_img_btn.config(state="normal"))
            self.root.after(0, lambda: self.draw_img_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_draw_btn.config(state="disabled"))

if __name__ == "__main__":
    root = tk.Tk()
    app = SwiccAdvancedHostApp(root)
    sv_ttk.set_theme("dark")
    
    style = ttk.Style()
    default_font = ("Segoe UI", 12)
    style.configure(".", font=default_font)
    style.configure("TLabel", font=default_font)
    style.configure("TEntry", font=default_font)
    style.configure("TCombobox", font=default_font)
    style.configure("TSpinbox", font=default_font)
    style.configure("TButton", font=default_font, padding=6)
    style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), padding=6)
    style.configure("TLabelframe.Label", font=("Segoe UI", 14, "bold"))
    
    if platform.system() == "Windows" and int(platform.release()) >= 10:
        pywinstyles.apply_style(root, "mica")
        pywinstyles.change_header_color(root, color="#202020")
    
    root.mainloop()