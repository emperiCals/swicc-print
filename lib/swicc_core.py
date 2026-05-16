import serial
import time
import threading
from typing import List, Dict, Any

class SwiccController:
    def __init__(self):
        self.serial_port = None
        self.is_connected = False

    def connect(self, port: str, baudrate: int = 115200) -> bool:
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=0)
            self.is_connected = True
            self.send_hex_state_str("00000880808080")
            return True
        except Exception:
            self.is_connected = False
            return False

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.send_hex_state_str("00000880808080")
            self.serial_port.close()
        self.is_connected = False

    def send_hex_state_str(self, hex_str: str):
        if not (self.serial_port and self.serial_port.is_open):
            return
        cmd = f"+IMM {hex_str}\r\n"
        try:
            self.serial_port.write(cmd.encode('utf-8'))
        except Exception:
            pass

    def send_raw_state(self, state_list: List[int]):
        hex_str = "".join(f"{b:02X}" for b in state_list)
        self.send_hex_state_str(hex_str)

    def calibrate_center(self, steps_x: int = 64, steps_y: int = 64, overdrive: int = 300, press_ms: int = 45, delay_ms: int = 35, cancel_event: threading.Event = None):
        """
        局域画布的绝对坐标校准
        """
        if not self.is_connected:
            return
        press_sec = press_ms / 1000.0
        delay_sec = delay_ms / 1000.0
        
        # 1. 向上强制碰撞画布极限 (UP)
        for _ in range(overdrive):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError()
            self.send_hex_state_str("00000080808080")
            time.sleep(press_sec)
            self.send_hex_state_str("00000880808080")
            time.sleep(delay_sec)
            
        # 2. 向左强制碰撞画布极限 (LEFT) - 归零至局部 (0, 0)
        for _ in range(overdrive):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError()
            self.send_hex_state_str("00000680808080")
            time.sleep(press_sec)
            self.send_hex_state_str("00000880808080")
            time.sleep(delay_sec)
            
        # 3. 精确向右平移至中心点 (RIGHT)
        for _ in range(steps_x):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError()
            self.send_hex_state_str("00000280808080")
            time.sleep(press_sec)
            self.send_hex_state_str("00000880808080")
            time.sleep(delay_sec)
            
        # 4. 精确向下平移至中心点 (DOWN)
        for _ in range(steps_y):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError()
            self.send_hex_state_str("00000480808080")
            time.sleep(press_sec)
            self.send_hex_state_str("00000880808080")
            time.sleep(delay_sec)

    def execute_vector_commands(self, commands: List[Dict[str, Any]], press_ms: int = 45, delay_ms: int = 35, cancel_event: threading.Event = None):
        if not self.is_connected:
            return
        press_sec = press_ms / 1000.0
        delay_sec = delay_ms / 1000.0
        current_pen_pressed = False
        
        for cmd in commands:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError()
            
            cmd_type = cmd.get("type")
            if cmd_type == "pen_down":
                current_pen_pressed = True
                continue
            elif cmd_type == "pen_up":
                current_pen_pressed = False
                continue
            elif cmd_type == "move":
                dx = cmd.get("dx", 0)
                dy = cmd.get("dy", 0)
                # 0x04代表按下A键落笔
                button_mask = 0x04 if current_pen_pressed else 0x00
                
                if dx != 0:
                    dir_mask = 0x02 if dx > 0 else 0x06
                    for _ in range(abs(dx)):
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError()
                        state = [0x00, button_mask, dir_mask, 0x80, 0x80, 0x80, 0x80]
                        self.send_raw_state(state)
                        time.sleep(press_sec)
                        
                        state = [0x00, button_mask, 0x08, 0x80, 0x80, 0x80, 0x80]
                        self.send_raw_state(state)
                        time.sleep(delay_sec)
                        
                if dy != 0:
                    dir_mask = 0x04 if dy > 0 else 0x00
                    for _ in range(abs(dy)):
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError()
                        state = [0x00, button_mask, dir_mask, 0x80, 0x80, 0x80, 0x80]
                        self.send_raw_state(state)
                        time.sleep(press_sec)
                        
                        state = [0x00, button_mask, 0x08, 0x80, 0x80, 0x80, 0x80]
                        self.send_raw_state(state)
                        time.sleep(delay_sec)