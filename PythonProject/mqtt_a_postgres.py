# Nombre de archivo sugerido: mqtt_a_postgres.py
# Este script corre en tu PC/Servidor, NO en el ESP32.

import paho.mqtt.client as mqtt
import psycopg2
import json
import hashlib
from Crypto.Cipher import AES
import time
import os
# --- Configuración MQTT ---
MQTT_BROKER_HOST = "test.mosquitto.org"
MQTT_BROKER_PORT = 1883
# Tópico al que se suscribe, debe ser el mismo al que publica tu ESP32.
# Tu función publicar_estado2 en el archivo mqtt.py del ESP32 publica a "WokwiToLeo"
MQTT_TOPIC_SUSCRIPCION = "WokwiToLeo"

# --- Configuración PostgreSQL (usa tus credenciales) ---
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASSWORD = "Jero0609"  # Tu contraseña
DB_NAME = "Iot"  # Tu base de datos

# --- Clave de Encriptación (debe ser la misma que en tu ESP32 mqtt.py) ---
KEY = hashlib.sha256(b"1o7ESP*").digest()


def desencriptar_mensaje(msg_payload_bytes):
    """
    Desencripta el payload del mensaje MQTT.
    Espera que el payload sea IV (16 bytes) + ciphertext.
    """
    try:
        if len(msg_payload_bytes) < 16:  # Mínimo 16 bytes para el IV
            print("Error al desencriptar: Payload demasiado corto para contener IV.")
            return None

        iv = msg_payload_bytes[:16]
        ciphertext = msg_payload_bytes[16:]

        if not ciphertext:  # No hay datos después del IV
            print("Error al desencriptar: No hay ciphertext después del IV.")
            return None

        cipher = AES.new(KEY, AES.MODE_CBC, iv)
        decrypted_padded_bytes = cipher.decrypt(ciphertext)
        # Quitar padding de espacios. Tu ESP32 añade espacios.
        decrypted_str = decrypted_padded_bytes.decode('utf-8').strip()
        return decrypted_str
    except UnicodeDecodeError as ude:
        print(f"Error de decodificación Unicode al desencriptar: {ude}. Payload (hex): {msg_payload_bytes.hex()}")
        return None
    except Exception as e:
        print(f"Error general al desencriptar: {e}")
        return None


def guardar_en_db(mensaje_data_dict):  # mensaje_data_dict es el JSON parseado
    """
    Guarda los datos del mensaje en la tabla esp32_mqtt_datos.
    """
    conn = None
    cursor = None  # Inicializar cursor a None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()

        dispositivo_id = mensaje_data_dict.get("id")
        estado_actual = mensaje_data_dict.get("estado")
        # Guardar el JSON original como texto para la columna mensaje_completo
        mensaje_completo_str = json.dumps(mensaje_data_dict)

        if dispositivo_id is None or estado_actual is None:
            print(f"Datos incompletos en el diccionario JSON: {mensaje_data_dict}. No se guardará.")
            return

        # SQL para la tabla esp32_mqtt_datos (ajusta si tu tabla es diferente)
        sql = """
            INSERT INTO esp32_mqtt_datos (dispositivo_id, estado, mensaje_completo) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (dispositivo_id, estado_actual, mensaje_completo_str))

        conn.commit()
        print(f"Datos guardados en esp32_mqtt_datos: ID={dispositivo_id}, Estado={estado_actual}")

    except psycopg2.Error as db_err:
        print(f"Error de base de datos: {db_err}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Error general guardando en DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:  # Cerrar cursor si se abrió
            cursor.close()
        if conn:  # Cerrar conexión si se abrió
            conn.close()
            # print("Conexión a PostgreSQL cerrada.") # Puedes descomentar para más verbosidad


# Callback cuando se conecta al broker MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Conectado exitosamente al Broker MQTT: {MQTT_BROKER_HOST}")
        client.subscribe(MQTT_TOPIC_SUSCRIPCION)
        print(f"Suscrito al tópico: {MQTT_TOPIC_SUSCRIPCION}")
    else:
        print(f"Fallo al conectar al broker MQTT, código de error: {rc}")
        print("Verifica que el broker esté activo y accesible, y que las credenciales (si las hubiera) sean correctas.")
        print("Si es un broker público, podría estar temporalmente inaccesible o tener restricciones.")


# Callback cuando se recibe un mensaje MQTT
def on_message(client, userdata, msg):
    print(f"\n--- Mensaje Recibido --- ({time.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"Tópico: {msg.topic}")
    # print(f"Payload (crudo en bytes): {msg.payload}") # Descomentar para depuración detallada
    print(f"Payload (hex): {msg.payload.hex()}")  # Imprimir en hexadecimal es más útil para data binaria

    mensaje_desencriptado_str = desencriptar_mensaje(msg.payload)

    if mensaje_desencriptado_str:
        print(f"Mensaje Desencriptado: {mensaje_desencriptado_str}")
        try:
            datos_json = json.loads(mensaje_desencriptado_str)
            if isinstance(datos_json, dict):  # Asegurarse que es un diccionario
                guardar_en_db(datos_json)
            else:
                print(f"Error: El JSON desencriptado no es un diccionario: {datos_json}")
        except json.JSONDecodeError:
            print(f"Error: El mensaje desencriptado no es un JSON válido: '{mensaje_desencriptado_str}'")
        except Exception as e:
            print(f"Error procesando el JSON o guardando en DB: {e}")
    else:
        print("No se pudo procesar el mensaje (falló la desencriptación, mensaje vacío o no válido).")


# --- Programa Principal ---
if __name__ == '__main__':
    # Verificación de importación de Crypto al inicio
    try:
        from Crypto.Cipher import AES
        print("Librería Crypto (AES) importada correctamente para el script intermediario.")
    except ModuleNotFoundError:
        print("¡¡ERROR CRÍTICO!! No se pudo importar Crypto.Cipher.AES para el script intermediario.")
        print("Por favor, instala 'pycryptodome' (pip install pycryptodome) en el entorno Python donde ejecutas este script.")
        exit()
    except Exception as e:
        print(f"Error importando Crypto.Cipher.AES: {e}")
        exit()

    # Configurar cliente MQTT
    mqtt_client_id = f"mqtt_a_postgres_logger_{os.getpid()}"
    print(f"Usando MQTT Client ID: {mqtt_client_id}") # Nuevo print

    # Intenta especificar la versión de la API de Callbacks si usas paho-mqtt >= 2.0
    # Si no estás seguro, prueba primero sin ella, y si da error de callbacks, añádela.
    try:
        # Para paho-mqtt < 2.0.0
        # client = mqtt.Client(client_id=mqtt_client_id)

        # Para paho-mqtt >= 2.0.0 (intenta esta si la anterior no funciona o por si acaso)
        # pip show paho-mqtt  (para ver tu versión instalada)
        import paho.mqtt.client as mqtt # Asegúrate que mqtt esté bien definido aquí
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=mqtt_client_id)
        print("Cliente MQTT inicializado con CallbackAPIVersion.VERSION1.")

    except AttributeError: # Si CallbackAPIVersion no existe (paho-mqtt < 2.0.0)
        client = mqtt.Client(client_id=mqtt_client_id)
        print("Cliente MQTT inicializado (versión paho-mqtt < 2.0.0).")
    except Exception as e_init:
        print(f"Error inicializando cliente MQTT: {e_init}")
        exit()


    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Intentando conectar al broker MQTT: {MQTT_BROKER_HOST} en puerto {MQTT_BROKER_PORT}...")
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60) # keepalive=60 segundos
        print("Después de client.connect()... iniciando loop.") # Nuevo print
        client.loop_forever() # Mantiene el script corriendo y escuchando mensajes en un bucle bloqueante
        # Esta línea de abajo no debería alcanzarse si loop_forever funciona
        print("Saliendo de loop_forever()... esto no debería pasar normalmente.")

    except ConnectionRefusedError:
        print(f"Error: Conexión al broker MQTT rechazada. Verifica que el broker esté activo y accesible.")
    except OSError as e:
        print(f"Error de red o del sistema al intentar conectar al broker MQTT: {e}")
    except KeyboardInterrupt:
        print("\nInterrupción por teclado. Desconectando y saliendo...")
    except Exception as e:
        print(f"Ocurrió un error inesperado antes o durante el loop principal: {e}") # Error más genérico
    finally:
        print("Bloque finally alcanzado. Desconectando del broker MQTT...")
        client.disconnect()
        print("Cliente MQTT desconectado. Saliendo del script.")