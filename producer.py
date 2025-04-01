import websocket
import json
import time
import threading
import requests
from kafka import KafkaProducer
from datetime import datetime

# Configuración del productor Kafka
producer = KafkaProducer(bootstrap_servers='localhost:9092',
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Variables globales para los datos
latest_price = 0.0
latest_hash_rate = 0.0  # En EH/s
last_hash_rate_update = 0

# Función para obtener el hash rate cada 60 segundos
def update_hash_rate():
    global latest_hash_rate, last_hash_rate_update
    while True:
        try:
            response = requests.get("https://api.blockchain.info/stats")
            data = response.json()
            latest_hash_rate = data["hash_rate"] / 1e18  # Convertir a EH/s
            last_hash_rate_update = time.time()
            print(f"Hash rate actualizado: {latest_hash_rate} EH/s")
        except Exception as e:
            print(f"Error al obtener hash rate: {e}")
        time.sleep(60)

# Función para manejar mensajes del WebSocket
def on_message(ws, message):
    global latest_price
    data = json.loads(message)
    latest_price = float(data.get("bitcoin", latest_price))
    print(f"Precio recibido: {latest_price} USD")

def on_error(ws, error):
    print(f"Error en WebSocket: {error}")

def on_close(ws):
    print("Conexión WebSocket cerrada")

def on_open(ws):
    print("Conexión WebSocket abierta")

# Función para enviar mensajes a Kafka cada segundo
def send_to_kafka():
    global latest_price, latest_hash_rate
    while True:
        timestamp = datetime.utcnow().isoformat()
        message = {
            "timestamp": timestamp,
            "price": latest_price,
            "hash_rate": latest_hash_rate
        }
        producer.send('BitcoinData', message)
        print(f"Enviado: {message}")
        time.sleep(1)

# Iniciar el WebSocket en un hilo
ws = websocket.WebSocketApp("wss://ws.coincap.io/prices?assets=bitcoin",
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close,
                            on_open=on_open)
ws_thread = threading.Thread(target=ws.run_forever)
ws_thread.daemon = True
ws_thread.start()

# Iniciar la actualización del hash rate en otro hilo
hash_rate_thread = threading.Thread(target=update_hash_rate)
hash_rate_thread.daemon = True
hash_rate_thread.start()

# Iniciar el envío de mensajes a Kafka en el hilo principal
send_to_kafka()