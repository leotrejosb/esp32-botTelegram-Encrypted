import network
import socket
import json

def lanzarServidor():
    ssid = "ESPLEON"
    password = "123456789"
    red = network.WLAN(network.AP_IF)
    red.active(True)
    red.config(essid=ssid, password=password, authmode=network.AUTH_WPA2_PSK)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        print('Conectado a: ', addr)
        try:
            solicitud = conn.recv(1024).decode()  # Decodificar la solicitud de binario a string
            print('Solicitud recibida: ', solicitud)

            # Verificar si la solicitud es un GET
            if solicitud.startswith("GET"):
                # Extraer la línea de la solicitud que contiene los parámetros
                lineas = solicitud.split("\r\n")
                primera_linea = lineas[0]  # La primera línea contiene el método, la URL y el protocolo
                url = primera_linea.split(" ")[1]  # Extraer la URL

                # Verificar si la URL contiene parámetros
                if "?" in url:
                    parametros = url.split("?")[1]  # Obtener los parámetros después de ?
                    parametros = parametros.split("&")  # Separar los parámetros
                    datos = {}
                    for p in parametros:
                        if "=" in p:
                            clave, valor = p.split("=")
                            datos[clave] = valor

                    # Obtener el SSID y la contraseña
                    ssid_usuario = datos.get("ssid", "")
                    password_usuario = datos.get("password", "")

                    # Imprimir los valores
                    print("SSID:", ssid_usuario)
                    print("Contraseña:", password_usuario)

                    # Crear una respuesta JSON
                    respuesta_json = {
                        "status": "success",
                        "ssid": ssid_usuario,
                        "password": password_usuario
                    }
                    respuesta_json_str = json.dumps(respuesta_json)
                    print("Respuesta JSON:", respuesta_json_str)

                # Enviar la respuesta HTML
                try:
                    archivohtml = open("index.html", "r")
                    html = archivohtml.read()
                    archivohtml.close()
                except OSError as e:
                    print("Error al abrir el archivo HTML:", e)
                    html = "<html><body><h1>Error: Archivo no encontrado</h1></body></html>"

                cabecera = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                dato = cabecera + html
                conn.sendall(dato.encode())
        except OSError as e:
            print("Error de conexión:", e)
        finally:
            conn.close()