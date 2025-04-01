import json
from kafka import KafkaConsumer
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import threading
import queue

# Configuración del consumidor Kafka
consumer = KafkaConsumer('BitcoinData',
                        bootstrap_servers='localhost:9092',
                        auto_offset_reset='latest',
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')))

# Colas para datos (máximo 10,000 puntos)
max_points = 10000
timestamps = deque(maxlen=max_points)
prices = deque(maxlen=max_points)
hash_rates = deque(maxlen=max_points)

# Cola para comunicación entre hilos
data_queue = queue.Queue()

# Función para leer mensajes de Kafka
def read_kafka():
    for message in consumer:
        data = message.value
        data_queue.put(data)

# Configuración de la gráfica
fig, ax1 = plt.subplots(figsize=(10, 6))
ax2 = ax1.twinx()

ax1.set_xlabel('Tiempo')
ax1.set_ylabel('Precio (USD)', color='tab:blue')
ax2.set_ylabel('Hash Rate (EH/s)', color='tab:red')

line1, = ax1.plot([], [], 'b-', label='Precio Bitcoin')
line2, = ax2.plot([], [], 'r-', label='Hash Rate')

ax1.legend(loc='upper left')
ax2.legend(loc='upper right')

# Función de actualización de la gráfica
def update(frame):
    while not data_queue.empty():
        data = data_queue.get()
        timestamps.append(data['timestamp'])
        prices.append(data['price'])
        hash_rates.append(data['hash_rate'])
    
    line1.set_data(range(len(prices)), prices)
    line2.set_data(range(len(hash_rates)), hash_rates)
    
    ax1.relim()
    ax1.autoscale_view()
    ax2.relim()
    ax2.autoscale_view()
    
    return line1, line2

# Iniciar la lectura de Kafka en un hilo
kafka_thread = threading.Thread(target=read_kafka)
kafka_thread.daemon = True
kafka_thread.start()

# Animación de la gráfica
ani = FuncAnimation(fig, update, interval=1000)
plt.show()