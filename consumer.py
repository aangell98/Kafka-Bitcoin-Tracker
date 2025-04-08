import json
from kafka import KafkaConsumer
import threading
import queue
from datetime import datetime, timedelta
import requests  # Para obtener datos históricos
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

# Función para obtener datos históricos (ejemplo con CryptoCompare)
def get_historical_data():
    """
    Obtiene datos históricos de precios de Bitcoin (hasta 10,000 minutos si es posible).
    Devuelve una lista de tuplas (timestamp, price).
    """
    url = "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=2000"  # Ajusta el límite según necesidades
    response = requests.get(url)
    data = response.json()
    if data['Response'] != 'Success':
        print(f"Error al obtener datos históricos: {data['Message']}")
        return []
    hist_data = data['Data']['Data']
    return [(datetime.fromtimestamp(entry['time']), entry['close']) for entry in hist_data]

# Función para procesar datos históricos en velas
def process_historical_candles(historical_prices):
    """
    Convierte datos históricos de precios en velas de 5 minutos.
    Devuelve una lista de tuplas (timestamp, open, high, low, close).
    """
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
    return candles[:MAX_POINTS]  # Limitar a 10,000 velas

# Cargar datos históricos al inicio
historical_prices = get_historical_data()
price_data.extend(historical_prices[-MAX_POINTS:])  # Limitar a 10,000 puntos más recientes
candle_data.extend(process_historical_candles(historical_prices)[-MAX_POINTS:])  # Limitar a 10,000 velas

def read_kafka():
    for message in consumer:
        data_queue.put(message.value)

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

# Iniciar hilos de Kafka y procesamiento
threading.Thread(target=read_kafka, daemon=True).start()
threading.Thread(target=process_data, daemon=True).start()

# App Dash
app = dash.Dash(__name__)
app.title = "Bitcoin en tiempo real"

app.layout = html.Div([
    html.H1("Bitcoin en tiempo real"),
    dcc.Graph(id='line-chart'),
    dcc.Graph(id='candlestick-chart'),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Actualiza cada 1000ms
        n_intervals=0
    )
])

@app.callback(
    Output('line-chart', 'figure'),
    Output('candlestick-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graphs(n):
    line_fig = go.Figure()
    if price_data:
        timestamps, prices = zip(*price_data)
        line_fig.add_trace(go.Scatter(x=timestamps, y=prices, mode='lines', name='Precio'))
        line_fig.update_layout(title='Precio en tiempo real', yaxis_title='USD')

    candle_fig = go.Figure()
    if candle_data:
        timestamps, opens, highs, lows, closes = zip(*candle_data)
        candle_fig.add_trace(go.Candlestick(
            x=timestamps,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name='Velas'
        ))
        candle_fig.update_layout(title='Velas de 5 minutos', yaxis_title='USD')

    return line_fig, candle_fig

if __name__ == '__main__':
    app.run(debug=True)