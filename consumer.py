import json
import time
from kafka import KafkaConsumer
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
from matplotlib.animation import FuncAnimation
from collections import deque
import threading
import queue
from datetime import datetime, timedelta

# Configuración del consumidor Kafka
consumer = KafkaConsumer('BitcoinData',
                         bootstrap_servers='localhost:9092',
                         auto_offset_reset='latest',
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

# Colas y variables para datos
data_queue = queue.Queue()
interval = 60  # Intervalo de 1 minuto en segundos
current_interval_start = None
prices_in_interval = []
ohlc_data = deque(maxlen=10000 // interval)  # Almacenar ~10,000 puntos
hash_rate_data = deque(maxlen=10000 // interval)

# Leer mensajes de Kafka
def read_kafka():
    for message in consumer:
        data_queue.put(message.value)

# Procesar datos y calcular OHLC
def process_data():
    global current_interval_start, prices_in_interval, ohlc_data, hash_rate_data
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            timestamp = datetime.fromisoformat(data['timestamp'])
            price = data['price']
            hash_rate = data['hash_rate']
            
            if current_interval_start is None:
                current_interval_start = timestamp.replace(second=0, microsecond=0)
            
            if timestamp < current_interval_start + timedelta(seconds=interval):
                prices_in_interval.append(price)
            else:
                if prices_in_interval:
                    open_price = prices_in_interval[0]
                    high_price = max(prices_in_interval)
                    low_price = min(prices_in_interval)
                    close_price = prices_in_interval[-1]
                    ohlc_data.append((mdates.date2num(current_interval_start), 
                                    open_price, high_price, low_price, close_price))
                    hash_rate_data.append((mdates.date2num(current_interval_start), hash_rate))
                current_interval_start = timestamp.replace(second=0, microsecond=0)
                prices_in_interval = [price]
        time.sleep(0.1)

# Configuración de la gráfica
fig, ax1 = plt.subplots(figsize=(12, 6))
ax2 = ax1.twinx()

ax1.set_xlabel('Tiempo')
ax1.set_ylabel('Precio (USD)', color='tab:blue')
ax2.set_ylabel('Hash Rate (EH/s)', color='tab:red')

# Actualizar la gráfica
def update(frame):
    ax1.clear()
    ax2.clear()
    
    if ohlc_data:
        candlestick_ohlc(ax1, ohlc_data, width=0.0005, colorup='g', colordown='r')
        ax1.set_xlim(mdates.date2num(current_interval_start - timedelta(minutes=10)), 
                     mdates.date2num(current_interval_start))
        ax1.xaxis_date()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    if hash_rate_data:
        dates, rates = zip(*hash_rate_data)
        ax2.plot(dates, rates, 'r-', label='Hash Rate')
    
    ax1.set_ylabel('Precio (USD)', color='tab:blue')
    ax2.set_ylabel('Hash Rate (EH/s)', color='tab:red')
    ax1.legend(['Precio'], loc='upper left')
    ax2.legend(['Hash Rate'], loc='upper right')

# Iniciar hilos
kafka_thread = threading.Thread(target=read_kafka)
kafka_thread.daemon = True
kafka_thread.start()

process_thread = threading.Thread(target=process_data)
process_thread.daemon = True
process_thread.start()

# Animación
ani = FuncAnimation(fig, update, interval=1000)
plt.show()