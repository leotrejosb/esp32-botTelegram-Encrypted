# manejo_MQTT.py
import machine
import ubinascii
import time
from umqtt.robust import MQTTClient
from machine import Pin
import json  # Importar la librería json

def conectar_mqtt():
    host = "test.mosquitto.org"
    port = "1883"
    client_id = ubinascii.hexlify(machine.unique_id())
    cliente = MQTTClient(client_id, host, port)
    try:
        cliente.connect()
        return cliente
    except OSError as e:
        print(f'Error conectando a MQTT:{e}')
        return False

def publicar_mensaje_prueba(cliente):
    topico = "ESPLEON"
    while True:
        cliente.publish(topico, 'ESPLEON')
        time.sleep(5)

def publicar_estado(cliente):
    topico = "ESPLEON"
    boton = Pin(5, Pin.IN, Pin.PULL_UP)
    estado_actual = 5
    estado_pasado = 2
    while True:
        estado_actual = boton.value()
        if estado_actual != estado_pasado:
            cliente.publish(topico, str(boton.value()))
            estado_pasado = estado_actual

def sub_cb(topic, msg):
    print(topic, msg)
    try:
        # Decodificar el mensaje JSON
        data = json.loads(msg.decode())

        if data["id"] == "ESPLEON":  # Verificar el ID
            print("ho")
            led = Pin(2, Pin.OUT)  # Configura el LED en el pin 4
            if data["estado"] == 1:  # Si el estado es 1, encender el LED
                led.on()
            elif data["estado"] == 0:  # Si el estado es 0, apagar el LED
                led.off()
    except Exception as e:
        print(f'Error procesando el mensaje: {e}')

def suscribirse(cliente, topico):
    cliente.set_callback(sub_cb)
    cliente.subscribe(topico)
    print("aca")
    while True:
        cliente.wait_msg()