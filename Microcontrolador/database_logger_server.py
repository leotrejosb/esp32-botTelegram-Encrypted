import psycopg2
import paho.mqtt.client as mqtt
import json
import os
import time
from datetime import datetime

# --- Configuración de la Base de Datos (AJUSTA ESTOS VALORES SEGÚN TU ENTORNO) ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")  # Puerto estándar de PostgreSQL. Tu ejemplo usaba 5000, verifica.
DB_USER = os.getenv("DB_USER", "postgres")  # Usuario de tu BD
DB_PASSWORD = os.getenv("DB_PASSWORD", "Jero0609")  # Contraseña de tu archivo insercion_data_base.py
DB_NAME = os.getenv("DB_NAME", "Iot")  # Nombre de BD de tu archivo insercion_data_base.py
LOG_TABLE_NAME = "logs_mqtt"  # Nombre sugerido para la tabla de logs estructurados

# --- Configuración MQTT ---
MQTT_BROKER_HOST = "test.mosquitto.org"  # Broker público, o el tuyo
MQTT_BROKER_PORT = 1883
MQTT_LOGGING_TOPIC = "esp32/device_logs"  # Tópico donde el ESP32 publicará los logs


def get_db_connection():
    """Establece y retorna una conexión a la base de datos, con reintentos."""
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            print(f"DATABASE: Conectado a PostgreSQL (Host: {DB_HOST}, DB: {DB_NAME})")
            return conn
        except psycopg2.OperationalError as e:
            print(f"DATABASE: Error al conectar a PostgreSQL: {e}. Reintentando en 10 segundos...")
            time.sleep(10)


def setup_database_table(conn):
    """Asegura que la tabla de logs exista con la estructura deseada."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {LOG_TABLE_NAME} (
                    id SERIAL PRIMARY KEY,
                    timestamp_utc TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, /* Recibido del ESP o generado */
                    device_id VARCHAR(255),
                    direction VARCHAR(10) NOT NULL, /* SENT or RECEIVED por el ESP32 */
                    mqtt_topic_operational VARCHAR(255) NOT NULL, /* Tópico original de la operación */
                    payload_operational TEXT, /* Payload del mensaje original (idealmente plaintext) */
                    is_encrypted_on_op_topic BOOLEAN DEFAULT FALSE,
                    operation_success BOOLEAN,
                    error_details TEXT
                );
            """)
            conn.commit()
            print(f"DATABASE: Tabla '{LOG_TABLE_NAME}' verificada/creada.")
    except psycopg2.Error as e:
        print(f"DATABASE: Error al configurar la tabla: {e}")
        conn.rollback()


def insert_log_to_db(conn, log_data):
    """Inserta una entrada de log en la base de datos."""
    try:
        with conn.cursor() as cursor:
            query = f"""
                INSERT INTO {LOG_TABLE_NAME}
                (timestamp_utc, device_id, direction, mqtt_topic_operational, payload_operational, is_encrypted_on_op_topic, operation_success, error_details)
                VALUES (TO_TIMESTAMP(%s), %s, %s, %s, %s, %s, %s, %s);
            """
            # El ESP32 envía 'timestamp_utc' como epoch. TO_TIMESTAMP lo convierte.
            cursor.execute(query, (
                log_data.get("timestamp_utc", time.time()),  # Fallback a tiempo actual del servidor si no viene
                log_data.get("device_id"),
                log_data.get("direction"),
                log_data.get("original_topic"),  # Este es el tópico operativo
                log_data.get("message_logged"),  # Este es el payload operativo
                log_data.get("is_encrypted_on_op_topic", False),
                log_data.get("operation_success", True),
                log_data.get("error_details")
            ))
            conn.commit()
            # print(f"DATABASE: Log insertado para device {log_data.get('device_id')} en tópico {log_data.get('original_topic')}")
    except psycopg2.Error as e:
        print(f"DATABASE: Error al insertar log: {e} - Data: {log_data}")
        conn.rollback()
    except Exception as ex:
        print(f"DATABASE: Error inesperado durante la inserción: {ex} - Data: {log_data}")
        if conn and not conn.closed:
            conn.rollback()


# Callbacks MQTT
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"MQTT_LOGGER: Conectado al Broker MQTT ({MQTT_BROKER_HOST})")
        client.subscribe(MQTT_LOGGING_TOPIC)
        print(f"MQTT_LOGGER: Suscrito al tópico de logs '{MQTT_LOGGING_TOPIC}'")
    else:
        print(f"MQTT_LOGGER: Falló la conexión al broker, código de retorno {rc}")


def on_message(client, userdata, msg):
    db_conn = userdata['db_conn']
    if db_conn.closed:
        print("DATABASE: Conexión cerrada, intentando reconectar...")
        db_conn = get_db_connection()
        if db_conn.closed:  # Si sigue cerrada después del intento
            print("DATABASE: No se pudo reconectar. Mensaje de log perdido.")
            return
        userdata['db_conn'] = db_conn  # Actualizar la conexión en userdata
        setup_database_table(db_conn)  # Asegurar que la tabla exista si es una nueva conexión

    # print(f"MQTT_LOGGER: Mensaje de log recibido en '{msg.topic}'")
    try:
        payload_str = msg.payload.decode('utf-8')
        log_data = json.loads(payload_str)
        insert_log_to_db(db_conn, log_data)
    except json.JSONDecodeError:
        print(f"MQTT_LOGGER: Error decodificando JSON del log: {msg.payload.decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"MQTT_LOGGER: Error procesando mensaje de log: {e}")


def run_logger():
    db_connection = get_db_connection()
    if db_connection.closed:  # Verifica si la conexión es None o está cerrada
        print("CRITICAL: No se pudo conectar a la base de datos. El logger no puede iniciar.")
        return

    setup_database_table(db_connection)

    # Paho MQTT v1.x usa CallbackAPIVersion.VERSION1 por defecto
    mqtt_client = mqtt.Client(client_id="db_logger_service_esp32_002")  # Cambia el client_id si es necesario
    mqtt_client.user_data_set({'db_conn': db_connection})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        print(f"MQTT_LOGGER: Intentando conectar al broker {MQTT_BROKER_HOST}...")
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("MQTT_LOGGER: Deteniendo logger...")
    except Exception as e:
        print(f"MQTT_LOGGER: Ocurrió un error: {e}")
    finally:
        if mqtt_client.is_connected():
            mqtt_client.disconnect()
        print("MQTT_LOGGER: Desconectado del MQTT Broker.")
        if db_connection and not db_connection.closed:
            db_connection.close()
            print("DATABASE: Conexión a PostgreSQL cerrada.")


if __name__ == "__main__":
    print("Iniciando Servicio de Logger MQTT a PostgreSQL...")
    run_logger()