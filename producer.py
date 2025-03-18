import time
import json
import requests
from kafka import KafkaProducer

# Configuración del producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# URLs de las APIs
BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
HASHRATE_API = "https://api.blockchain.info/stats"

def fetch_bitcoin_data():
    try:
        # Obtener precio desde Binance
        price_response = requests.get(BINANCE_API)
        price_response.raise_for_status()  # Verifica errores HTTP
        price_data = price_response.json()
        price = float(price_data['price'])  # Precio en USDT

        # Obtener hash rate desde Blockchain
        hashrate_response = requests.get(HASHRATE_API)
        hashrate_response.raise_for_status()
        hashrate_data = hashrate_response.json()
        hashrate = hashrate_data['hash_rate']

        return {
            'timestamp': time.time(),
            'price': price,
            'hashrate': hashrate
        }
    except requests.RequestException as e:
        print(f"Error al obtener datos: {e}")
        return None

# Enviar datos a Kafka cada segundo
while True:
    data = fetch_bitcoin_data()
    if data:
        producer.send('BitcoinData', value=data)
        print(f"Enviado: {data}")
    else:
        print("No se enviaron datos debido a un error")
    time.sleep(1)  # Actualizar cada segundo