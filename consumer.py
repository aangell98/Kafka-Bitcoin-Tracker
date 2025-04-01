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

# Variables y colas para datos
data_queue = queue.Queue()
interval = 60  # Intervalo de 1 minuto en segundos
current_interval_start = None
prices_in_interval = []
ohlc_data = deque(maxlen=10000 // interval)  # Velas completas
hash_rate_data = deque(maxlen=10000 // interval)
current_ohlc = None  # Vela en formación

# Leer mensajes de Kafka
def read_kafka():
    for message in consumer:
        data_queue.put(message.value)

# Procesar datos y calcular OHLC
def process_data():
    global current_interval_start, prices_in_interval, ohlc_data, hash_rate_data, current_ohlc
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            timestamp = datetime.fromisoformat(data['timestamp'])
            price = data['price']
            hash_rate = data['hash_rate']
            
            if current_interval_start is None:
                # Iniciar el primer intervalo
                current_interval_start = timestamp.replace(second=0, microsecond=0)
                prices_in_interval = [price]
                current_ohlc = [mdates.date2num(current_interval_start), price, price, price, price]
            else:
                # Verificar si el precio pertenece al intervalo actual
                if timestamp < current_interval_start + timedelta(seconds=interval):
                    prices_in_interval.append(price)
                    # Actualizar la vela en formación
                    current_ohlc[1] = prices_in_interval[0]  # Open (primer precio)
                    current_ohlc[2] = max(prices_in_interval)  # High (máximo)
                    current_ohlc[3] = min(prices_in_interval)  # Low (mínimo)
                    current_ohlc[4] = prices_in_interval[-1]  # Close (último precio)
                else:
                    # Finalizar la vela actual y empezar una nueva
                    if prices_in_interval:
                        ohlc_data.append(tuple(current_ohlc))
                        hash_rate_data.append((mdates.date2num(current_interval_start), hash_rate))
                    current_interval_start = timestamp.replace(second=0, microsecond=0)
                    prices_in_interval = [price]
                    current_ohlc = [mdates.date2num(current_interval_start), price, price, price, price]
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
    
    # Mostrar velas completas
    if ohlc_data:
        candlestick_ohlc(ax1, ohlc_data, width=0.0005, colorup='g', colordown='r')
    
    # Mostrar la vela en formación (con menor opacidad para distinguirla)
    if current_ohlc:
        candlestick_ohlc(ax1, [current_ohlc], width=0.0005, colorup='g', colordown='r', alpha=0.5)
    
    # Mostrar hash rate
    if hash_rate_data:
        dates, rates = zip(*hash_rate_data)
        ax2.plot(dates, rates, 'r-', label='Hash Rate')
    
    # Ajustar límites y formato del eje X
    if ohlc_data or current_ohlc:
        all_dates = [d[0] for d in ohlc_data] + ([current_ohlc[0]] if current_ohlc else [])
        ax1.set_xlim(min(all_dates) - 0.001, max(all_dates) + 0.001)
        ax1.xaxis_date()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # Configurar etiquetas y leyendas
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

# Animación para actualizar la gráfica cada segundo
ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)
plt.show()