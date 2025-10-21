import psycopg2

conexion = psycopg2.connect(
    host="localhost",
    port="5000",
    user="postgres",
    password="Jero0609",
    database = "Iot"
)