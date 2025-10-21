import machine
import ubinascii
import time
from umqtt.robust import MQTTClient
from machine import Pin
import ujson
import uos
from ucryptolib import aes
import hashlib
import json  # Importar la librería json

# Generar clave AES (compartida en ambos dispositivos)
KEY = hashlib.sha256(b"1o7ESP*").digest()  # Usar bytes y digest()


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


# --- tarea ------
# En esta funcion le publicaremos desde el micro a wowik
def publicar_estado2(cliente):
    topico = "WokwiToLeo"
    boton = Pin(5, Pin.IN, Pin.PULL_UP)  # El pin 5 está configurado como entrada con pull-up
    estado_actual = 5
    estado_pasado = 2

    while True:
        estado_actual = boton.value()

        if estado_actual != estado_pasado:
            time.sleep(2)  # 50 ms de espera para estabilizar el estado
            # Crear mensaje JSON
            mensaje_json = json.dumps({"id": "ESPLEON",  # Campo requerido por el suscriptor
                                       "estado": estado_actual})

            # Encriptar
            iv = uos.urandom(16)  # IV único por mensaje
            cipher = aes(KEY, 2, iv)  # MODE_CBC = 2
            padded = mensaje_json + " " * (16 - len(mensaje_json) % 16)  # Padding
            encrypted = cipher.encrypt(padded)

            # Combinar IV + mensaje encriptado
            mensaje = iv + encrypted
            print(f"Estado inicial del botón (Pin 5): {estado_actual}")
            print("\nFin\n")
            # Publicar
            cliente.publish(topico, mensaje)
            estado_pasado = estado_actual
        time.sleep(0.1)  # Pequeña espera para evitar demasiados mensajes


# Esta funcion es para suscribir a el topico que se publique desde el wokwi
def sub_cb2(topic, msg):
    print("holaa")
    try:
        # Extraer IV (primeros 16 bytes) y datos encriptados
        iv = msg[:16]
        ciphertext = msg[16:]

        # Desencriptar
        decipher = aes(KEY, 2, iv)  # Misma clave y IV
        decrypted_padded = decipher.decrypt(ciphertext)
        decrypted = decrypted_padded.decode().strip()  # Quitar padding
        print(decrypted)
        # Parsear JSON
        data = json.loads(decrypted)
        if data["id"] == "ESPLEON":  # Verificar el ID
            led = Pin(2, Pin.OUT)  # Configura el LED en el pin 4
            if data["estado"] == 1:  # Si el estado es 1, encender el LED
                led.on()
            elif data["estado"] == 0:  # Si el estado es 0, apagar el LED
                led.off()
    except Exception as e:
        print(f'Error procesando el mensaje: {e}')


def suscribirse2(cliente):
    topico = "LeoToWowik"
    cliente.set_callback(sub_cb2)
    cliente.subscribe(topico)
    while True:
        cliente.check_msg()