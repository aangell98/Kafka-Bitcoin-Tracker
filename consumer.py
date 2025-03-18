import json
from kafka import KafkaConsumer
import matplotlib.pyplot as plt
from collections import deque
import time

# Configuración del consumer
consumer = KafkaConsumer(
    'BitcoinData',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest'
)

# Configuración de la gráfica
MAX_POINTS = 10000  # Hasta 10,000 medidas
times = deque(maxlen=MAX_POINTS)
prices = deque(maxlen=MAX_POINTS)
hashrates = deque(maxlen=MAX_POINTS)

plt.ion()  # Modo interactivo
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()  # Segundo eje Y para hash rate

line1, = ax1.plot([], [], 'b-', label='Price (USD)')
line2, = ax2.plot([], [], 'r-', label='Hash Rate')
ax1.set_xlabel('Time (seconds since start)')
ax1.set_ylabel('Price (USD)', color='b')
ax2.set_ylabel('Hash Rate', color='r')
plt.title('Bitcoin Price vs Hash Rate')

# Consumir mensajes y actualizar gráfica
start_time = time.time()
for message in consumer:
    data = message.value
    times.append(data['timestamp'] - start_time)  # Tiempo relativo
    prices.append(data['price'])
    hashrates.append(data['hashrate'])

    # Actualizar datos de la gráfica
    line1.set_xdata(times)
    line1.set_ydata(prices)
    line2.set_xdata(times)
    line2.set_ydata(hashrates)

    # Ajustar límites
    ax1.relim()
    ax1.autoscale_view()
    ax2.relim()
    ax2.autoscale_view()

    plt.legend([line1, line2], ['Price', 'Hash Rate'])
    plt.draw()
    plt.pause(0.01)  # Pausa breve para actualizar