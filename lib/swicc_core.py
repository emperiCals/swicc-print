import serial
import time
import threading
import json
import gc
from typing import List, Dict, Any, Callable, Tuple

class Button:
    MINUS   = (0, 0x01)
    PLUS    = (0, 0x02)
    L_CLICK = (0, 0x04)
    R_CLICK = (0, 0x08)
    HOME    = (0, 0x10)
    CAPTURE = (0, 0x20)
    
    Y       = (1, 0x01)
    B       = (1, 0x02)
    A       = (1, 0x04)
    X       = (1, 0x08)
    L       = (1, 0x10)
    R       = (1, 0x20)
    ZL      = (1, 0x40)
    ZR      = (1, 0x80)

class DPad:
    UP         = 0x00
    UP_RIGHT   = 0x01
    RIGHT      = 0x02
    DOWN_RIGHT = 0x03
    DOWN       = 0x04
    DOWN_LEFT  = 0x05
    LEFT       = 0x06
    UP_LEFT    = 0x07
    NEUTRAL    = 0x08

class SwiccController:
    def __init__(self, log_callback: Callable[[str], None] = None):
        self.serial_port = None
        self.is_connected = False
        self.log_callback = log_callback
        self.read_thread_active = False
        self.read_thread_obj = None
        self.keep_alive_thread_obj = None
        
        self.state = [0x00, 0x00, 0x08, 0x80, 0x80, 0x80, 0x80]
        
        self.pending_ack = None
        self.ack_event = threading.Event()

    def connect(self, port: str, baudrate: int = 115200) -> bool:
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=0.05)
            self.is_connected = True
            
            self.read_thread_active = True
            self.read_thread_obj = threading.Thread(target=self._serial_read_loop, daemon=True)
            self.read_thread_obj.start()
            
            self.keep_alive_thread_obj = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self.keep_alive_thread_obj.start()
            
            self._wake_and_reset_board()
            
            self.reset_state()
            self.flush_state()
            
            time.sleep(0.1)
            cmd = "+MODE_QUERY\r\n"
            self.serial_port.write(cmd.encode('utf-8'))
            return True
        except Exception:
            self.is_connected = False
            gc.collect()
            return False

    def disconnect(self):
        self.is_connected = False
        self.read_thread_active = False
        if self.serial_port and self.serial_port.is_open:
            self.reset_state()
            self.flush_state()
            self.serial_port.close()
        gc.collect()

    def _serial_read_loop(self):
        loop_counter = 0
        while self.read_thread_active and self.serial_port and self.serial_port.is_open:
            try:
                line = self.serial_port.readline()
                if line:
                    decoded_str = line.decode('utf-8', errors='ignore').strip()
                    if decoded_str:
                        if decoded_str.startswith("ACK_"):
                            self.pending_ack = decoded_str
                            self.ack_event.set()
                            
                        if self.log_callback:
                            self.log_callback(decoded_str)
            except Exception:
                pass
                
            loop_counter += 1
            if loop_counter > 10000:
                gc.collect()
                loop_counter = 0
                
            time.sleep(0.001)

    def _keep_alive_loop(self):
        while self.read_thread_active and self.serial_port and self.serial_port.is_open:
            time.sleep(2.5)
            try:
                self.serial_port.write(b'\r\n')
            except Exception:
                pass

    def _wake_and_reset_board(self):
        if not (self.serial_port and self.serial_port.is_open):
            return
        try:
            self.serial_port.write(b'\x03')
            time.sleep(0.1)
            self.serial_port.write(b'\x02')
            time.sleep(0.1)
            self.serial_port.write(b'\x04')
            time.sleep(0.6) 
        except Exception:
            pass

    def wait_for_ack(self, expected: str, timeout: float = 2.0) -> bool:
        self.ack_event.clear()
        start = time.time()
        while time.time() - start < timeout:
            if self.ack_event.wait(0.1):
                if self.pending_ack == expected:
                    return True
                self.ack_event.clear()
        return False

    def write_file_to_hw(self, target_filename: str, raw_data: str, progress_cb: Callable[[int, int], None] = None) -> bool:
        if not self.is_connected: return False
        
        self.serial_port.write(f"+FS_OPEN {target_filename}\r\n".encode('utf-8'))
        if not self.wait_for_ack("ACK_FS_OPEN", 3.0): return False
            
        chunk_size = 64
        total_chunks = (len(raw_data) + chunk_size - 1) // chunk_size
        
        for i in range(total_chunks):
            chunk = raw_data[i*chunk_size : (i+1)*chunk_size]
            cmd = f"+FS_WRITE {chunk}\r\n"
            self.serial_port.write(cmd.encode('utf-8'))
            if not self.wait_for_ack("ACK_FS_WRITE", 1.0):
                self.serial_port.write(b"+FS_CLOSE\r\n")
                gc.collect()
                return False
            if progress_cb: progress_cb(i + 1, total_chunks)
                
        self.serial_port.write(b"+FS_CLOSE\r\n")
        gc.collect()
        return self.wait_for_ack("ACK_FS_CLOSE", 3.0)

    def burn_macro(self, json_steps: list, slot_index: int, progress_cb: Callable[[int, int], None] = None) -> bool:
        filename = f"macro_{slot_index}.json"
        raw_data = json.dumps(json_steps, separators=(',', ':'))
        return self.write_file_to_hw(filename, raw_data, progress_cb)

    def hot_update_firmware(self, python_code: str, progress_cb: Callable[[int, int], None] = None) -> bool:
        success = self.write_file_to_hw("update_main.py", python_code, progress_cb)
        if success:
            self.serial_port.write(b"+SYS_REBOOT\r\n")
            self.wait_for_ack("ACK_SYS_REBOOT", 1.0)
            time.sleep(1.0)
        return success

    def set_button(self, btn: Tuple[int, int], pressed: bool):
        byte_idx, mask = btn
        if pressed: self.state[byte_idx] |= mask
        else: self.state[byte_idx] &= ~mask

    def set_dpad(self, dpad_value: int):
        self.state[2] = dpad_value

    def set_left_stick(self, x: int, y: int):
        self.state[3], self.state[4] = x, y

    def set_right_stick(self, x: int, y: int):
        self.state[5], self.state[6] = x, y

    def reset_state(self):
        self.state = [0x00, 0x00, 0x08, 0x80, 0x80, 0x80, 0x80]

    def get_state_hex(self) -> str:
        return "".join(f"{b:02X}" for b in self.state)

    def flush_state(self):
        self.send_hex_state_str(self.get_state_hex())

    def send_hex_state_str(self, hex_str: str):
        if not (self.serial_port and self.serial_port.is_open): return
        try: self.serial_port.write(f"+IMM {hex_str}\r\n".encode('utf-8'))
        except: pass

    def send_raw_state(self, state_list: List[int]):
        self.send_hex_state_str("".join(f"{b:02X}" for b in state_list))

    def switch_hardware_mode(self, mode_command: str):
        if not (self.serial_port and self.serial_port.is_open): return
        try:
            if mode_command == "+MODE_BURN":
                self.serial_port.write(f"{mode_command}\r\n".encode('utf-8'))
            else:
                self._wake_and_reset_board()
                self.serial_port.write(f"{mode_command}\r\n".encode('utf-8'))
        except: pass

    def calibrate_center(self, steps_x=64, steps_y=64, overdrive=300, press_ms=45, delay_ms=35, cancel_event=None):
        if not self.is_connected: return
        p_s, d_s = press_ms / 1000.0, delay_ms / 1000.0
        
        def push(cmd_hex, loops):
            for _ in range(loops):
                if cancel_event and cancel_event.is_set(): raise InterruptedError()
                self.send_hex_state_str(cmd_hex)
                time.sleep(p_s)
                self.send_hex_state_str("00000880808080")
                time.sleep(d_s)
                
        push("00000080808080", overdrive) 
        push("00000680808080", overdrive) 
        push("00000280808080", steps_x)   
        push("00000480808080", steps_y)   
            
        self.reset_state()
        self.flush_state()

    def execute_vector_commands(self, commands: List[Dict[str, Any]], press_ms=45, delay_ms=35, cancel_event=None):
        if not self.is_connected: return
        p_s, d_s = press_ms / 1000.0, delay_ms / 1000.0
        pen_pressed = False
        
        for cmd in commands:
            if cancel_event and cancel_event.is_set(): raise InterruptedError()
            
            ctype = cmd.get("type")
            if ctype == "pen_down": pen_pressed = True; continue
            elif ctype == "pen_up": pen_pressed = False; continue
            elif ctype == "move":
                dx, dy = cmd.get("dx", 0), cmd.get("dy", 0)
                btn_mask = 0x04 if pen_pressed else 0x00
                
                def mv(delta, mask1, mask2):
                    dir_mask = mask1 if delta > 0 else mask2
                    for _ in range(abs(delta)):
                        if cancel_event and cancel_event.is_set(): raise InterruptedError()
                        self.send_raw_state([0x00, btn_mask, dir_mask, 0x80, 0x80, 0x80, 0x80])
                        time.sleep(p_s)
                        self.send_raw_state([0x00, btn_mask, 0x08, 0x80, 0x80, 0x80, 0x80])
                        time.sleep(d_s)
                        
                if dx != 0: mv(dx, 0x02, 0x06)
                if dy != 0: mv(dy, 0x04, 0x00)
                        
        self.reset_state()
        self.flush_state()
        gc.collect()