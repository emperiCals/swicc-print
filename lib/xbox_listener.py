import threading
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class XboxListener:
    """
    独立封装的Xbox手柄硬件抽象层，专门处理XInput到虚拟状态机的映射。
    解耦了pygame依赖，可独立运行于独立线程中。
    """
    def __init__(self, controller_instance, dpad_enum, button_enum, update_callback):
        self.controller = controller_instance
        self.dpad_enum = dpad_enum
        self.button_enum = button_enum
        self.update_callback = update_callback
        
        self.is_active = False
        self.listener_thread = None
        self.joystick = None
        
        self.button_map = {
            0: self.button_enum.B, 
            1: self.button_enum.A, 
            2: self.button_enum.Y, 
            3: self.button_enum.X, 
            4: self.button_enum.L, 
            5: self.button_enum.R, 
            6: self.button_enum.MINUS, 
            7: self.button_enum.PLUS, 
            8: self.button_enum.L_CLICK, 
            9: self.button_enum.R_CLICK, 
            10: self.button_enum.HOME 
        }

    def start(self) -> bool:
        if not PYGAME_AVAILABLE:
            return False

        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            return False
            
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        self.is_active = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        return True

    def stop(self):
        self.is_active = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1.0)
        if PYGAME_AVAILABLE and pygame.joystick.get_init():
            pygame.joystick.quit()

    def is_running(self) -> bool:
        return self.is_active

    def _process_axis(self, val, deadzone=0.15):
        if abs(val) < deadzone: 
            return 128
        return int((val + 1.0) * 127.5)

    def _listen_loop(self):
        local_last_hex = self.controller.get_state_hex()
        
        while self.is_active:
            pygame.event.pump()
            
            for k, v in self.button_map.items():
                self.controller.set_button(v, self.joystick.get_button(k))

            hat_val = self.joystick.get_hat(0)
            dpad_val = self.dpad_enum.NEUTRAL
            if hat_val == (0, 1): dpad_val = self.dpad_enum.UP
            elif hat_val == (0, -1): dpad_val = self.dpad_enum.DOWN
            elif hat_val == (-1, 0): dpad_val = self.dpad_enum.LEFT
            elif hat_val == (1, 0): dpad_val = self.dpad_enum.RIGHT
            elif hat_val == (1, 1): dpad_val = self.dpad_enum.UP_RIGHT
            elif hat_val == (-1, 1): dpad_val = self.dpad_enum.UP_LEFT
            elif hat_val == (1, -1): dpad_val = self.dpad_enum.DOWN_RIGHT
            elif hat_val == (-1, -1): dpad_val = self.dpad_enum.DOWN_LEFT
            self.controller.set_dpad(dpad_val)

            lx = self.joystick.get_axis(0)
            ly = self.joystick.get_axis(1)
            rx = self.joystick.get_axis(2)
            ry = self.joystick.get_axis(3)
            lt = self.joystick.get_axis(4)
            rt = self.joystick.get_axis(5)

            self.controller.set_left_stick(self._process_axis(lx), self._process_axis(ly))
            self.controller.set_right_stick(self._process_axis(rx), self._process_axis(ry))

            self.controller.set_button(self.button_enum.ZL, lt > 0)
            self.controller.set_button(self.button_enum.ZR, rt > 0)

            current_hex = self.controller.get_state_hex()
            if current_hex != local_last_hex:
                self.update_callback()
                local_last_hex = current_hex
            
            time.sleep(0.01)