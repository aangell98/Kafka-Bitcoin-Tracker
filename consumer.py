import json
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import time
import threading
import queue
from kafka import KafkaConsumer
import pandas as pd

# Configuración del consumidor Kafka
consumer = KafkaConsumer('BitcoinData',
                         bootstrap_servers='localhost:9092',
                         auto_offset_reset='latest',
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')))

# Cola para datos en tiempo real
data_queue = queue.Queue()

# Variables globales
all_data = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close'])
current_filter = "day"  # Filtro inicial
fig = go.Figure()  # Gráfico inicial

# Obtener datos históricos diarios (hasta 2000 días)
def get_historical_daily_data():
    url = "https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit=2000"
    response = requests.get(url)
    data = response.json()
    if data['Response'] != 'Success':
        print(f"Error al obtener datos históricos: {data['Message']}")
        return pd.DataFrame()
    hist_data = data['Data']['Data']
    df = pd.DataFrame(hist_data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close']]

# Obtener datos históricos por hora (últimas 24 horas)
def get_historical_hourly_data():
    url = "https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&limit=24"
    response = requests.get(url)
    data = response.json()
    if data['Response'] != 'Success':
        print(f"Error al obtener datos por hora: {data['Message']}")
        return pd.DataFrame()
    hist_data = data['Data']['Data']
    df = pd.DataFrame(hist_data)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close']]

# Procesar datos en tiempo real y gestionar el cierre de velas
def process_real_time_data():
    global all_data
    current_candle = None
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None)
            price = data['price']

            # Determinar el intervalo según el filtro activo
            if current_filter == "hour":
                interval = timedelta(hours=1)
            elif current_filter == "day":
                interval = timedelta(days=1)
            elif current_filter == "week":
                interval = timedelta(weeks=1)
            elif current_filter == "month":
                interval = timedelta(days=30)  # Aproximación para un mes
            else:
                interval = timedelta(days=1)

            # Iniciar una nueva vela si no hay una actual o si el tiempo supera el intervalo
            if current_candle is None or timestamp >= current_candle['end_time']:
                if current_candle:
                    # Añadir la vela completada a los datos históricos
                    new_row = pd.DataFrame({
                        'time': [current_candle['start_time']],
                        'open': [current_candle['open']],
                        'high': [current_candle['high']],
                        'low': [current_candle['low']],
                        'close': [current_candle['close']]
                    })
                    all_data = pd.concat([all_data, new_row]).sort_values('time').reset_index(drop=True)
                # Iniciar una nueva vela
                start_time = timestamp.replace(second=0, microsecond=0)
                end_time = start_time + interval
                current_candle = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price
                }
            else:
                # Actualizar la vela en formación
                current_candle['high'] = max(current_candle['high'], price)
                current_candle['low'] = min(current_candle['low'], price)
                current_candle['close'] = price
        time.sleep(0.1)

# Leer mensajes de Kafka
def read_kafka():
    for message in consumer:
        data_queue.put(message.value)

# Actualizar los datos del gráfico según el filtro
def update_plot():
    global all_data, current_filter
    df = all_data.copy()

    if not df.empty:
        df.set_index('time', inplace=True)
        if current_filter == "hour":
            df_resampled = df.resample('1H').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        elif current_filter == "day":
            df_resampled = df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        elif current_filter == "week":
            df_resampled = df.resample('1W').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        elif current_filter == "month":
            df_resampled = df.resample('1M').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        else:
            df_resampled = df
        df_resampled = df_resampled.reset_index()

        # Actualizar los datos del gráfico existente
        with fig.batch_update():
            fig.data[0].x = df_resampled['time']
            fig.data[0].open = df_resampled['open']
            fig.data[0].high = df_resampled['high']
            fig.data[0].low = df_resampled['low']
            fig.data[0].close = df_resampled['close']
            fig.update_layout(title=f"Bitcoin - {current_filter.capitalize()}")

# Cargar datos históricos iniciales
all_data = pd.concat([get_historical_daily_data(), get_historical_hourly_data()]).drop_duplicates(subset='time')

# Crear el gráfico inicial con botones
fig = go.Figure(data=[go.Candlestick(
    x=all_data['time'],
    open=all_data['open'],
    high=all_data['high'],
    low=all_data['low'],
    close=all_data['close'],
    name='Velas'
)])

fig.update_layout(
    title=f"Bitcoin - {current_filter.capitalize()}",
    xaxis_title="Tiempo",
    yaxis_title="Precio (USD)",
    xaxis_rangeslider_visible=False,
    dragmode='zoom',
    updatemenus=[dict(
        type="buttons",
        direction="right",
        x=0.05,
        y=1.2,
        buttons=[
            dict(label="Hora", method="update", args=[{"visible": [True]}, {"title": "Bitcoin - Hora"}]),
            dict(label="Día", method="update", args=[{"visible": [True]}, {"title": "Bitcoin - Día"}]),
            dict(label="Semana", method="update", args=[{"visible": [True]}, {"title": "Bitcoin - Semana"}]),
            dict(label="Mes", method="update", args=[{"visible": [True]}, {"title": "Bitcoin - Mes"}]),
        ],
        active=1  # Día como filtro predeterminado
    )]
)

# Mostrar el gráfico una sola vez
fig.show()

# Iniciar hilos
kafka_thread = threading.Thread(target=read_kafka, daemon=True)
kafka_thread.start()

process_thread = threading.Thread(target=process_real_time_data, daemon=True)
process_thread.start()

# Función para animar el gráfico
def animate():
    while True:
        update_plot()
        time.sleep(1)  # Actualizar cada segundo

animate_thread = threading.Thread(target=animate, daemon=True)
animate_thread.start()

# Mantener el programa en ejecución
while True:
    time.sleep(1)