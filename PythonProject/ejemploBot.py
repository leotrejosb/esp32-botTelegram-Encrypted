import telebot
import paho.mqtt.publish as publish
import json
import hashlib
import os  # Para os.urandom
from Crypto.Cipher import AES
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Configuración ---
BOT_TOKEN = "7996737283:AAGlzm77JAOs_DgUKgnAuFBwAhhAJtNjCP0"  # Tu token de Bot
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
# IMPORTANTE: Este tópico debe ser el que tu ESP32 está escuchando.
# En el código anterior del ESP32, se suscribía a "WokwiToLeo".
MQTT_TOPIC_TO_ESP = "WokwiToLeo"

# Clave de encriptación (debe ser idéntica a la del ESP32)
# hashlib.sha256(...).digest() produce 32 bytes.
KEY = hashlib.sha256(b"1o7ESP*").digest()

bot = telebot.TeleBot(BOT_TOKEN)


# --- Función de Encriptación ---
def encrypt_payload(payload_str):
    """
    Encripta el payload string usando AES CBC con la KEY global y un IV aleatorio.
    Replica el padding de espacios del ESP32.
    Retorna: bytes (iv + encrypted_data)
    """
    try:
        iv = os.urandom(16)  # IV único por mensaje (16 bytes para AES)
        # Crear objeto AES. AES.MODE_CBC es el modo correcto.
        cipher = AES.new(KEY, AES.MODE_CBC, iv)

        # Padding: añadir espacios hasta que la longitud sea múltiplo de 16 (tamaño de bloque AES)
        # Replicando: mensaje_json + " " * (16 - len(mensaje_json) % 16)
        # Asegurarse de que el padding se añade correctamente incluso si len % 16 es 0
        padding_length = 16 - (len(payload_str) % 16)
        padded_payload_str = payload_str + (" " * padding_length)

        # Convertir a bytes antes de encriptar
        padded_payload_bytes = padded_payload_str.encode('utf-8')

        encrypted_data = cipher.encrypt(padded_payload_bytes)

        # Combinar IV + mensaje encriptado
        return iv + encrypted_data
    except Exception as e:
        print(f"Error durante la encriptación: {e}")
        raise  # Propagar el error para que la función que llama sepa que falló


# --- Handlers del Bot ---

@bot.message_handler(commands=["menu"])
def menu_handler(message):  # Renombrado para evitar conflictos
    markup = InlineKeyboardMarkup()
    btn_on = InlineKeyboardButton("💡 Encender LED", callback_data="encender")
    btn_off = InlineKeyboardButton("🌑 Apagar LED", callback_data="apagar")
    markup.add(btn_on, btn_off)
    bot.send_message(message.chat.id, "Selecciona una opción:", reply_markup=markup)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "MENSAJE DE BIENVENIDA \n /ID para conocer su ID \n /menu para controlar el LED")


@bot.message_handler(commands=['ID'])
def send_ID(message):
    bot.reply_to(message, f"Su ID es: {message.chat.id}")


@bot.message_handler(commands=['encender'])
def encender_cmd(message):
    try:
        payload_dict = {"id": "ESPLEON", "estado": 1}
        payload_json_str = json.dumps(payload_dict)
        encrypted_message_with_iv = encrypt_payload(payload_json_str)

        publish.single(MQTT_TOPIC_TO_ESP, payload=encrypted_message_with_iv, hostname=MQTT_BROKER, port=MQTT_PORT)
        bot.send_message(message.chat.id, "*¡Comando para encender LED enviado!* ✅", parse_mode="Markdown")
        print(f"Publicado (encender) en {MQTT_TOPIC_TO_ESP}: {payload_dict} (encriptado)")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error al enviar el comando de encendido.")
        print(f"Error en encender_cmd: {e}")


@bot.message_handler(commands=['apagar'])
def apagar_cmd(message):
    try:
        payload_dict = {"id": "ESPLEON", "estado": 0}
        payload_json_str = json.dumps(payload_dict)
        encrypted_message_with_iv = encrypt_payload(payload_json_str)

        publish.single(MQTT_TOPIC_TO_ESP, payload=encrypted_message_with_iv, hostname=MQTT_BROKER, port=MQTT_PORT)
        bot.send_message(message.chat.id, "<b>¡Comando para apagar LED enviado!</b> ❌", parse_mode="HTML")
        print(f"Publicado (apagar) en {MQTT_TOPIC_TO_ESP}: {payload_dict} (encriptado)")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error al enviar el comando de apagado.")
        print(f"Error en apagar_cmd: {e}")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    action = call.data
    new_state = -1

    if action == "encender":
        new_state = 1
        response_text = "🔆 LED encendido."
        success_message = "✅ ¡Listo! El comando para encender el LED ha sido enviado."
    elif action == "apagar":
        new_state = 0
        response_text = "🌑 LED apagado."
        success_message = "❌ ¡Comando para apagar LED enviado correctamente!"
    else:
        bot.answer_callback_query(call.id, "Acción desconocida.")
        return

    try:
        payload_dict = {"id": "ESPLEON", "estado": new_state}
        payload_json_str = json.dumps(payload_dict)
        encrypted_message_with_iv = encrypt_payload(payload_json_str)

        publish.single(MQTT_TOPIC_TO_ESP, payload=encrypted_message_with_iv, hostname=MQTT_BROKER, port=MQTT_PORT)

        bot.answer_callback_query(call.id, response_text)
        # Usar edit_message_text para cambiar el mensaje original de los botones
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=call.message.text + f"\n\n*{success_message}*", parse_mode="Markdown")
        print(f"Publicado (callback {action}) en {MQTT_TOPIC_TO_ESP}: {payload_dict} (encriptado)")

    except Exception as e:
        bot.answer_callback_query(call.id, "Error al enviar comando.")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=call.message.text + "\n\n⚠️ Error al procesar tu solicitud.")
        print(f"Error en callback_handler ({action}): {e}")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Comando no reconocido. Usa /menu para ver las opciones.")


if __name__ == '__main__':
    print("Bot de Telegram iniciando...")


    bot.infinity_polling()