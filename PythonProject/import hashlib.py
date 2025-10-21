import hashlib

# La misma frase secreta que usas en tu ESP32
frase_secreta = b"1o7ESP*"

# Generar los bytes de la clave (igual que en tu ESP32)
key_bytes = hashlib.sha256(frase_secreta).digest()

# Convertir los bytes de la clave a un string hexadecimal
key_hex_para_nodered = key_bytes.hex()

print(f"La KEY que debes usar en la variable KEY_HEX de Node-RED es:")
print(key_hex_para_nodered)
print(f"Tiene una longitud de: {len(key_hex_para_nodered)} caracteres")