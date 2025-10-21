# Esto corre en tu PC/Servidor, NO en el ESP32
from flask import Flask, request, jsonify
import psycopg2
# import psycopg2.extras # No lo necesitas para inserciones simples

app = Flask(__name__)

# --- Configuración de la Base de Datos PostgreSQL ---
# Usa tus credenciales que ya sabes que funcionan
DB_HOST = "localhost"
DB_PORT = "5432" # Tu puerto correcto
DB_NAME = "Iot"    # Tu base de datos
DB_USER = "postgres" # Tu usuario
DB_PASS = "Jero0609" # Tu contraseña

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except psycopg2.OperationalError as e: # Captura específica para errores de conexión
        print(f"Error conectando a la base de datos: {e}")
        return None
    except Exception as e:
        print(f"Error general en get_db_connection: {e}")
        return None

@app.route('/guardar_log_esp', methods=['POST']) # Nueva ruta para guardar logs
def guardar_log_esp():
    conn = None # Inicializar conn a None
    try:
        datos_recibidos = request.get_json() # Espera un JSON del ESP32
        print(f"Datos recibidos del ESP32: {datos_recibidos}")

        # Extraer el mensaje que enviará el ESP32
        # Asumimos que el ESP32 enviará un JSON como: {"comentario_esp": "mensaje desde esp"}
        mensaje_esp = datos_recibidos.get('comentario_esp')

        if not mensaje_esp: # Verificar que el mensaje no esté vacío
            return jsonify({"estado": "error", "mensaje": "Falta el campo 'comentario_esp'"}), 400

        conn = get_db_connection()
        if not conn:
             return jsonify({"estado": "error", "mensaje": "No se pudo conectar a la base de datos"}), 500

        cursor = conn.cursor()
        
        # Tu lógica de inserción, adaptada para usar la variable mensaje_esp
        sql = """INSERT INTO esp32_mqtt_datos (dispositivo_id, estado, mensaje_completo) VALUES (%s, %s, %s)""" # Usar placeholders %s
        cursor.execute(sql, (mensaje_esp,)) # Pasar los valores como una tupla
        
        conn.commit()
        print("¡Inserción en public.logs exitosa!")

        return jsonify({"estado": "exito", "mensaje": "Log guardado correctamente"}), 201

    except psycopg2.OperationalError as e:
        print(f"Error de base de datos en /guardar_log_esp: {e}")
        if conn:
            conn.rollback() # Revertir cambios si hubo un error en la transacción
        return jsonify({"estado": "error", "mensaje": f"Error de base de datos: {e}"}), 500
    except Exception as e:
        print(f"Error general en /guardar_log_esp: {e}")
        if conn:
            conn.rollback()
        return jsonify({"estado": "error", "mensaje": f"Error general: {e}"}), 500
    finally:
        if conn:
            cursor.close() # Asegurarse de que el cursor se cierre si se abrió
            conn.close()
            print("Conexión a PostgreSQL cerrada.")

if __name__ == '__main__':
    # Ejecuta el servidor Flask.
    # Usa '0.0.0.0' para que sea accesible desde otros dispositivos en tu red local.
    app.run(host='0.0.0.0', port=5000, debug=True) # Puedes cambiar el puerto 5000 si lo deseas