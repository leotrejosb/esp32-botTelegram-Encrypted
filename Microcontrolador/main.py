# main.py (modificado)

from machine import Pin, unique_id  # unique_id para client_id si no se usa el de mqtt.py
import time
import ujson  # o json si es el que usa tu mqtt.py consistentemente
import uos  # Para uos.urandom

# Tus importaciones existentes
from claseDos import conexionInternet
# from ClaseTres import * # Comentado si no es necesario para esta funcionalidad combinada
# from ensayoMQTT import * # Comentado si no es necesario
from mqtt import conectar_mqtt, sub_cb2, KEY  # Importamos KEY y sub_cb2 directamente
from ucryptolib import aes  # Para la encriptación, si no está ya en mqtt.py
import hashlib  # Si KEY se define aquí en lugar de importarla

# --- Constantes y Configuraciones ---
# Tópico al que el ESP32 se suscribirá para escuchar mensajes
TOPICO_SUSCRIPCION = "LeoToWowik"  # El que usaba suscribirse2
# Tópico al que el ESP32 publicará los cambios de estado del botón
TOPICO_PUBLICACION = "WokwiToLeo"  # El que usaba publicar_estado2

# Configuración del botón
PIN_BOTON = 5


# (Opcional) Si KEY no se importa de mqtt.py, defínela aquí igual que en mqtt.py
# KEY = hashlib.sha256(b"1o7ESP*").digest()


def main_combinado():
    print("Iniciando modo combinado MQTT (Publicador y Suscriptor)...")

    # 1. Conectar a Internet
    if not conexionInternet():
        print("Error: No se pudo conectar a Internet. Reiniciando en 10s...")
        time.sleep(10)
        machine.reset()  # O maneja el error de otra forma
        return

    print("Conectado a Internet.")

    # 2. Conectar al Broker MQTT
    cliente = conectar_mqtt()
    if not cliente:
        print("Error: No se pudo conectar al Broker MQTT. Reiniciando en 10s...")
        time.sleep(10)
        machine.reset()  # O maneja el error de otra forma
        return

    print(f"Conectado al Broker MQTT. Escuchando en '{TOPICO_SUSCRIPCION}', publicando en '{TOPICO_PUBLICACION}'.")

    # 3. Configurar Suscripción MQTT
    cliente.set_callback(sub_cb2)  # sub_cb2 debe estar definida en tu mqtt.py (o importada)
    cliente.subscribe(TOPICO_SUSCRIPCION)
    print(f"Suscrito a: {TOPICO_SUSCRIPCION}")

    # 4. Configurar Publicación (basado en el botón)
    boton = Pin(PIN_BOTON, Pin.IN, Pin.PULL_UP)
    estado_pasado_boton = boton.value()  # Leer estado inicial del botón
    print(f"Estado inicial del botón (Pin {PIN_BOTON}): {estado_pasado_boton}")

    # 5. Bucle Principal: Escuchar y Publicar
    while True:
        try:
            # a. Revisar mensajes MQTT entrantes (no bloqueante)
            cliente.check_msg()

            # b. Lógica para publicar estado del botón
            estado_actual_boton = boton.value()

            if estado_actual_boton != estado_pasado_boton:
                # Debounce: espera un poco para estabilizar la lectura si hay rebotes
                time.sleep(1)
                estado_actual_boton = boton.value()  # Re-leer después del debounce

                if estado_actual_boton != estado_pasado_boton:  # Confirmar cambio
                    print(f"Botón cambió de {estado_pasado_boton} a {estado_actual_boton}. Publicando...")

                    # Crear mensaje JSON (como en tu publicar_estado2)
                    # Asegúrate de usar ujson o json consistentemente con lo que espera tu sub_cb2 y lo que usas en mqtt.py
                    mensaje_dict = {"id": "ESPLEON", "estado": estado_actual_boton}
                    mensaje_json_str = ujson.dumps(mensaje_dict)

                    # Encriptar (lógica de tu publicar_estado2)
                    iv = uos.urandom(16)
                    cipher = aes(KEY, 2, iv)  # aes.MODE_CBC = 2
                    # Padding
                    padded_mensaje_str = mensaje_json_str + " " * (16 - len(mensaje_json_str) % 16)
                    encrypted_bytes = cipher.encrypt(padded_mensaje_str.encode('utf-8'))  # Encriptar bytes

                    mensaje_a_publicar = iv + encrypted_bytes

                    # Publicar
                    cliente.publish(TOPICO_PUBLICACION, mensaje_a_publicar)
                    print(f"Publicado en {TOPICO_PUBLICACION}: {mensaje_dict}")

                    estado_pasado_boton = estado_actual_boton

            # Pequeña pausa para ceder el control y no saturar
            time.sleep_ms(100)  # 0.1 segundos

        except OSError as e:
            print(f"Error de OSError en el bucle principal (posible desconexión): {e}")
            print("Intentando reconectar MQTT...")
            time.sleep(5)
            # Intento simple de reconexión. Podrías hacer esto más robusto.
            cliente = conectar_mqtt()
            if cliente:
                cliente.set_callback(sub_cb2)
                cliente.subscribe(TOPICO_SUSCRIPCION)
                print("Reconectado y re-suscrito a MQTT.")
            else:
                print("Fallo al reconectar MQTT. Reiniciando en 10s...")
                time.sleep(10)
                machine.reset()  # O maneja el error de otra forma
        except Exception as e:
            print(f"Error inesperado en el bucle principal: {e}")
            time.sleep(5)  # Esperar un poco antes de continuar

if __name__ == "__main__":
    # Esperar un poco al inicio, opcional
    time.sleep(2)
    main_combinado()