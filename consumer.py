import json
from kafka import KafkaConsumer
import threading
import queue
from datetime import datetime, timedelta
import requests
import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go

# Variables globales
price_data = []  # Lista de (timestamp, price)
candle_data = []  # Lista de (timestamp, open, high, low, close)
MAX_POINTS = 10000
CANDLE_INTERVAL = timedelta(minutes=5)
current_candle = None
data_queue = queue.Queue()

# Kafka Consumer
consumer = KafkaConsumer(
    'BitcoinData',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Obtener datos históricos (ejemplo con CryptoCompare)
def get_historical_data():
    url = "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=2000"
    response = requests.get(url)
    data = response.json()
    if data['Response'] != 'Success':
        print(f"Error al obtener datos históricos: {data['Message']}")
        return []
    hist_data = data['Data']['Data']
    return [(datetime.fromtimestamp(entry['time']), entry['close']) for entry in hist_data]

# Procesar datos históricos en velas
def process_historical_candles(historical_prices):
    candles = []
    current = None
    for timestamp, price in sorted(historical_prices):
        if current is None or timestamp >= current['end_time']:
            if current:
                candles.append((
                    current['start_time'],
                    current['open'],
                    current['high'],
                    current['low'],
                    current['close']
                ))
            start_time = timestamp.replace(second=0, microsecond=0) - timedelta(minutes=timestamp.minute % 5)
            current = {
                'start_time': start_time,
                'end_time': start_time + CANDLE_INTERVAL,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
        else:
            current['high'] = max(current['high'], price)
            current['low'] = min(current['low'], price)
            current['close'] = price
    if current:
        candles.append((
            current['start_time'],
            current['open'],
            current['high'],
            current['low'],
            current['close']
        ))
    return candles[:MAX_POINTS]

# Cargar datos históricos al inicio
historical_prices = get_historical_data()
price_data.extend(historical_prices[-MAX_POINTS:])
candle_data.extend(process_historical_candles(historical_prices)[-MAX_POINTS:])

# Leer datos de Kafka
def read_kafka():
    for message in consumer:
        data_queue.put(message.value)

# Procesar datos en tiempo real
def process_data():
    global current_candle
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None)
            price = float(data['price'])

            # Actualizar gráfico lineal
            price_data.append((timestamp, price))
            if len(price_data) > MAX_POINTS:
                price_data.pop(0)

            # Gestionar velas
            if current_candle is None or timestamp >= current_candle['end_time']:
                if current_candle:
                    candle_data.append((
                        current_candle['start_time'],
                        current_candle['open'],
                        current_candle['high'],
                        current_candle['low'],
                        current_candle['close']
                    ))
                    if len(candle_data) > MAX_POINTS:
                        candle_data.pop(0)
                start_time = timestamp.replace(second=0, microsecond=0) - timedelta(minutes=timestamp.minute % 5)
                current_candle = {
                    'start_time': start_time,
                    'end_time': start_time + CANDLE_INTERVAL,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price
                }
            else:
                current_candle['high'] = max(current_candle['high'], price)
                current_candle['low'] = min(current_candle['low'], price)
                current_candle['close'] = price

# Iniciar hilos
threading.Thread(target=read_kafka, daemon=True).start()
threading.Thread(target=process_data, daemon=True).start()

# App Dash
app = dash.Dash(__name__)
app.title = "Bitcoin en tiempo real"

# Layout con figuras iniciales vacías
app.layout = html.Div([
    html.H1("Bitcoin en tiempo real"),
    dcc.Graph(id='line-chart', figure=go.Figure([go.Scatter(x=[], y=[], mode='lines')])),
    dcc.Graph(id='candlestick-chart', figure=go.Figure([go.Candlestick(x=[], open=[], high=[], low=[], close=[])])),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Actualiza cada 1 segundo
        n_intervals=0
    )
])

# Callback para actualizar solo los datos
@app.callback(
    [Output('line-chart', 'extendData'), Output('candlestick-chart', 'extendData')],
    Input('interval-component', 'n_intervals')
)
def update_graphs(n):
    # Datos para el gráfico lineal
    if price_data:
        timestamps, prices = zip(*price_data)
        line_data = dict(x=[list(timestamps)], y=[list(prices)])
    else:
        line_data = dict(x=[[]], y=[[]])

    # Datos para el gráfico de velas
    if candle_data:
        timestamps, opens, highs, lows, closes = zip(*candle_data)
        candle_data_dict = dict(
            x=[list(timestamps)],
            open=[list(opens)],
            high=[list(highs)],
            low=[list(lows)],
            close=[list(closes)]
        )
    else:
        candle_data_dict = dict(x=[[]], open=[[]], high=[[]], low=[[]], close=[[]])

    # Actualizar solo los datos de las trazas
    return (line_data, [0]), (candle_data_dict, [0])

if __name__ == '__main__':
    app.run(debug=True)