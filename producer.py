import websocket
import json
import time
import threading
import requests
from kafka import KafkaProducer
from datetime import datetime
import pytz

# Configuración de zona horaria local
local_timezone = pytz.timezone("Europe/Madrid")

# Configuración del productor Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Variables globales
latest_price = 0.0
latest_hash_rate = 0.0  # En EH/s
websocket_connected = False
latest_price_timestamp = None

# Función para obtener el hash rate cada 60 segundos
def update_hash_rate():
    global latest_hash_rate
    while True:
        try:
            response = requests.get("https://api.blockchain.info/stats")
            data = response.json()
            latest_hash_rate = data["hash_rate"]
            print(f"[{datetime.now(local_timezone).isoformat()}] Hash rate actualizado: {latest_hash_rate} TH/s")
        except Exception as e:
            print(f"Error al obtener hash rate: {e}")
        time.sleep(60)

# Manejar mensajes del WebSocket de Binance
def on_message(ws, message):
    global latest_price, latest_price_timestamp
    try:
        data = json.loads(message)
        price = float(data.get("c", latest_price))  # "c" es el precio de cierre en Binance
        if price != latest_price:
            latest_price = price
            latest_price_timestamp = datetime.now(local_timezone)
            print(f"[{latest_price_timestamp.isoformat()}] Precio actualizado: {latest_price} USD")
    except Exception as e:
        print(f"Error al procesar mensaje: {e}")

def on_error(ws, error):
    global websocket_connected
    print(f"Error en WebSocket: {error}")
    websocket_connected = False

def on_close(ws, close_status_code, close_msg):
    global websocket_connected
    print(f"Conexión WebSocket cerrada: {close_status_code} - {close_msg}")
    websocket_connected = False

def on_open(ws):
    global websocket_connected
    print("Conexión WebSocket abierta")
    websocket_connected = True

# Función para manejar la conexión WebSocket con reconexión
def run_websocket():
    global websocket_connected
    while True:
        if not websocket_connected:
            try:
                ws = websocket.WebSocketApp(
                    "wss://stream.binance.com:9443/ws/btcusdt@ticker",
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )
                ws_thread = threading.Thread(target=ws.run_forever)
                ws_thread.daemon = True
                ws_thread.start()
                time.sleep(5)  # Esperar antes de reintentar si falla
            except Exception as e:
                print(f"Error al iniciar WebSocket: {e}")
                time.sleep(5)
        time.sleep(1)

# Enviar datos a Kafka cada segundo
def send_to_kafka():
    global latest_price, latest_hash_rate
    while True:
        timestamp = datetime.now(local_timezone).isoformat()
        message = {
            "timestamp": timestamp,
            "price": latest_price,
            "hash_rate": latest_hash_rate
        }
        producer.send('BitcoinData', message)
        print(f"[{timestamp}] Enviado: {message}")
        time.sleep(1)

# Iniciar hilos
websocket_thread = threading.Thread(target=run_websocket, daemon=True)
websocket_thread.start()

hash_rate_thread = threading.Thread(target=update_hash_rate, daemon=True)
hash_rate_thread.start()

send_to_kafka()  # Ejecutar en el hilo principal
