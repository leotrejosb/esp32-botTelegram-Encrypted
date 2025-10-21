import machine
import ubinascii
import time
from umqtt.robust import MQTTClient
from machine import Pin
import ujson
from ensayoMQTT import *

# Parámetros del broker
BROKER = "test.mosquitto.org"
PORT = 1883  # Puerto explícito

# LED en el pin 4
led = Pin(4, Pin.OUT)

# Función callback que se llama al recibir un mensaje
def sub_cb(topic, msg):
    print("Mensaje recibido:", msg)
    try:
        datos = ujson.loads(msg)
        if datos.get("id") == topic.decode():
            estado = datos.get("estado")
            if estado == 1:
                led.value(1)
                print("LED encendido")
            else:
                led.value(0)
                print("LED apagado")
    except Exception as e:
        print("Error al procesar mensaje:", e)

# Conectar al broker MQTT
def conectar_mqtt():
    try:
        client = MQTTClient("ESPLEON", BROKER, port=PORT)
        client.set_callback(sub_cb)
        client.connect()
        print("Conectado a MQTT Broker:", BROKER)
        return client
    except Exception as e:
        print("Error al conectar al broker:", e)
        return None

# Suscribirse a un tópico
def suscribirse(client, topico):
    try:
        client.subscribe(topico)
        print("Suscrito al tópico:", topico)
        while True:
            client.wait_msg()
    except Exception as e:
        print("Error en suscripción:", e)

# Publicar estado (JSON)
def publicar_estado(client, topico, estado):
    try:
        mensaje = ujson.dumps({"id": "ESPLEON", "estado": estado})
        client.publish(topico, mensaje)
        print("Mensaje publicado:", mensaje)
    except Exception as e:
        print("Error al publicar mensaje:", e)

# Alias para compatibilidad con main.py (publicar recibe ya un JSON en string)
def publicar(client, topico, mensaje):
    try:
        client.publish(topico, mensaje)
        print("Mensaje publicado:", mensaje)
    except Exception as e:
        print("Error al publicar mensaje:", e)