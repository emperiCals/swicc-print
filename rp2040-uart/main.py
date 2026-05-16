import sys
import uselect
from machine import UART, Pin

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
poller = uselect.poll()
poller.register(sys.stdin, uselect.POLLIN)

def transparent_bridge():
    while True:
        if poller.poll(0):
            usb_data = sys.stdin.read(1)
            if usb_data:
                uart.write(usb_data.encode('utf-8'))
                
        if uart.any():
            uart_data = uart.read(uart.any())
            if uart_data:
                try:
                    sys.stdout.write(uart_data.decode('utf-8'))
                except Exception:
                    pass

if __name__ == '__main__':
    transparent_bridge()