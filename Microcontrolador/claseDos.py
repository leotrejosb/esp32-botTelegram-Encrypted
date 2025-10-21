from machine import Pin
import time
import network

def lecturaPin():
    led = Pin(4, Pin.OUT)  # Configuración del LED que controlas
    boton = Pin(5, Pin.IN, Pin.PULL_UP)  # Configuración del botón

    while True:

        led.value(boton.value())  # Si el botón está presionado, apaga el LED (valor bajo), si no, enciéndelo


# Configuración de la conexión WiFi
def conexionInternet():
    conteo = 0
    ledIndicador = Pin(2, Pin.OUT)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.scan()  # Scan for available access points
    sta_if.connect("UTP", "tecnologica")  # Connect to an AP


    while not sta_if.isconnected():
        ledIndicador.value (not ledIndicador.value())
        time.sleep(5)
        conteo += 1
        if conteo == 10:
            break
    if conteo < 10:
        ledIndicador.on()
        print ("Conexion exitosa")
        print("Dirección IP:", sta_if.ifconfig()[0])
        return True
    else:
        ledIndicador.off()
        print("Conexion no exitosa")
        return False


