import os
import sys
try:
    if "burn_flag.txt" in os.listdir():
        os.remove("burn_flag.txt")
        sys.exit(0)
except Exception:
    pass
import uselect
import gc
import json
import machine
import micropython
import uasyncio as asyncio
from machine import UART, Pin
micropython.kbd_intr(-1)
MODE_BRIDGE = 0
MODE_MACRO = 1
MODE_BURN = 2
MODE_NAMES = {
    MODE_BRIDGE: "BRIDGE",
    MODE_MACRO: "MACRO",
    MODE_BURN: "BURN"
}
CONFIG_FILE = "sys_config.json"
macro_files = ["macro_0.json", "macro_1.json", "macro_2.json"]

config = {"mode": MODE_BRIDGE, "macro_index": 0}
try:
    with open(CONFIG_FILE, "r") as f:
        config.update(json.load(f))
except Exception:
    pass

reset_cause = machine.reset_cause()
if reset_cause != machine.PWRON_RESET:
    if config["mode"] == MODE_MACRO:
        config["macro_index"] = (config["macro_index"] + 1) % len(macro_files)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception:
            pass

current_mode = config["mode"]
current_macro_index = config["macro_index"]
is_playing = (current_mode == MODE_MACRO)
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
def report_status():
    sys.stdout.write(f"[STATUS] MODE={MODE_NAMES.get(current_mode, 'UNKNOWN')}\n")

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"mode": current_mode, "macro_index": current_macro_index}, f)
    except Exception:
        pass

async def uart_usb_bridge_task():
    global current_mode, is_playing
    poller = uselect.poll()
    poller.register(sys.stdin, uselect.POLLIN)
    usb_buffer = ""
    transfer_file = None

    while current_mode != MODE_BURN:
        try:
            while poller.poll(0):
                usb_data = sys.stdin.read(1)
                if not usb_data:
                    break

                if usb_data == '\x03':
                    micropython.kbd_intr(3)
                    sys.exit(0)
                    
                if usb_data in ('\x01', '\x02', '\x04'):
                    continue
                    
                if current_mode == MODE_BRIDGE:
                    uart.write(usb_data.encode('utf-8'))
                
                if usb_data == '\n' or usb_data == '\r':
                    command = usb_buffer.strip()
                    usb_buffer = ""
                    
                    if not command:
                        continue

                    if command.startswith("+FS_OPEN "):
                        filename = command.split(" ")[1]
                        try:
                            transfer_file = open(filename, "w")
                            sys.stdout.write("ACK_FS_OPEN\n")
                        except Exception:
                            sys.stdout.write("ERR_FS_OPEN\n")
                    elif command.startswith("+FS_WRITE "):
                        data = command[10:]
                        if transfer_file:
                            transfer_file.write(data)
                            sys.stdout.write("ACK_FS_WRITE\n")
                    elif command == "+FS_CLOSE":
                        if transfer_file:
                            transfer_file.close()
                            transfer_file = None
                            sys.stdout.write("ACK_FS_CLOSE\n")
                            
                    # ---- 状态机与硬件控制 ----
                    elif command == "+SYS_REBOOT":
                        sys.stdout.write("ACK_SYS_REBOOT\n")
                        machine.reset() 
                        
                    elif command == "+MODE_QUERY":
                        report_status()
                        
                    elif command == "+MODE_BURN":
                        with open("burn_flag.txt", "w") as f:
                            f.write("1")
                        machine.reset()
                        
                    elif command == "+MODE_MACRO":
                        current_mode = MODE_MACRO
                        is_playing = True
                        save_config()
                        report_status()
                        
                    elif command == "+MODE_BRIDGE":
                        current_mode = MODE_BRIDGE
                        save_config()
                        report_status()
                else:
                    usb_buffer += usb_data
                    if len(usb_buffer) > 512:
                        usb_buffer = ""

            if uart.any():
                uart_data = uart.read(min(uart.any(), 64))
                if uart_data:
                    sys.stdout.write(uart_data.decode('utf-8', 'ignore'))
        except Exception:
            gc.collect()
        
        await asyncio.sleep(0.001)

async def macro_playback_task():
    global is_playing
    
    while current_mode != MODE_BURN:
        if current_mode == MODE_MACRO and is_playing:
            target_file = macro_files[current_macro_index]
            try:
                with open(target_file, "r") as f:
                    macro_data = json.load(f)
                    for step in macro_data:
                        if current_mode != MODE_MACRO or not is_playing:
                            break
                        state_str = step.get("state", "00000880808080")
                        duration_ms = step.get("duration", 100)
                        
                        cmd = f"+IMM {state_str}\r\n"
                        uart.write(cmd.encode('utf-8'))
                        await asyncio.sleep(duration_ms / 1000.0)
                        uart.write(b"+IMM 00000880808080\r\n")
                        await asyncio.sleep(0.035)
            except Exception:
                pass
            
            is_playing = False
        await asyncio.sleep(0.1)

async def main():
    bridge_task = asyncio.create_task(uart_usb_bridge_task())
    macro_task = asyncio.create_task(macro_playback_task())
    await asyncio.gather(bridge_task, macro_task)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        pass
    finally:
        micropython.kbd_intr(3)