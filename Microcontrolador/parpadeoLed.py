from machine import Pin
import time

def parpadeoLed():
    led = Pin(4, Pin.OUT)

    while True:
        led.value(1)  # Encender el LED
        time.sleep(1)  # Esperar 1 segundo
        led.value(0)  # Apagar el LED
        time.sleep(1)  # Esperar 1 segundo

parpadeoLed()