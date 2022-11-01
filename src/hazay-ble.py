from machine import UART, Pin
import time

led = Pin(25, Pin.OUT)

BLE_MODE_PIN = Pin(15 , Pin.IN , Pin.PULL_UP)

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

Name_BLE_Set                       = b"AT+BMHazayCargo #001\r\n"
Name_BLE_Query                     = b"AT+TM\r\n"

uart.write(Name_BLE_Query)
time.sleep_ms(100)
uart.write(Name_BLE_Set)
time.sleep_ms(100)

counter = 0

while True:
    counter += 1
    uart.write(str(counter))
    led.value(1)            #Set led turn on
    time.sleep(0.1)
    led.value(0)
    time.sleep(3)
            
        



