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
price_data = []  # Lista de (timestamp, price, hash_rate)
candle_data = []  # Lista de (timestamp, open, high, low, close)
MAX_POINTS = 10000
CANDLE_INTERVAL = timedelta(minutes=5)
current_candle = None
data_queue = queue.Queue()
last_price_update = 0  # Índice del último dato enviado al gráfico lineal
last_candle_update = 0  # Índice del último dato enviado al gráfico de velas

# Kafka Consumer
consumer = KafkaConsumer(
    'BitcoinData',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Obtener datos históricos de precios (CryptoCompare)
def get_historical_prices():
    url = "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=2000"
    response = requests.get(url)
    data = response.json()
    if data['Response'] != 'Success':
        print(f"Error al obtener datos históricos de precios: {data['Message']}")
        return []
    hist_data = data['Data']['Data']
    historical = [(datetime.fromtimestamp(entry['time']), entry['close']) for entry in hist_data]
    return historical

# Obtener datos históricos de hash rate (simulado, ya que Blockchain.info es incorrecto)
def get_historical_hash_rate():
    # Simulamos datos históricos de hash rate (en TH/s)
    # En la vida real, deberías obtener estos datos de una fuente confiable como BitInfoCharts o Glassnode
    start_time = datetime.now() - timedelta(days=2)
    historical = []
    for i in range(48):  # 48 puntos para 2 días (1 punto por hora)
        timestamp = start_time + timedelta(hours=i)
        # Simulamos un hash rate que varía entre 580M y 620M TH/s
        hash_rate = 600_000_000 + (i % 5) * 10_000_000  # Variación simulada
        historical.append((timestamp, hash_rate))
    return historical

# Combinar datos históricos de precios y hash rate
def get_historical_data():
    # Obtener precios históricos
    price_history = get_historical_prices()
    if not price_history:
        return []

    # Obtener hash rate histórico
    hash_rate_history = get_historical_hash_rate()
    if not hash_rate_history:
        return [(ts, price, 0.0) for ts, price in price_history]

    # Combinar datos interpolando el hash rate
    combined_data = []
    hash_rate_idx = 0
    for timestamp, price in price_history:
        while hash_rate_idx < len(hash_rate_history) - 1 and hash_rate_history[hash_rate_idx + 1][0] < timestamp:
            hash_rate_idx += 1
        if hash_rate_idx == len(hash_rate_history) - 1:
            hash_rate = hash_rate_history[-1][1]
        else:
            t0, h0 = hash_rate_history[hash_rate_idx]
            t1, h1 = hash_rate_history[hash_rate_idx + 1]
            time_diff = (t1 - t0).total_seconds()
            weight = (timestamp - t0).total_seconds() / time_diff if time_diff > 0 else 0
            hash_rate = h0 + (h1 - h0) * weight
        combined_data.append((timestamp, price, hash_rate))

    combined_data.sort(key=lambda x: x[0])
    return combined_data

# Procesar datos históricos en velas (sin hash_rate, solo precio)
def process_historical_candles(historical_prices):
    candles = []
    current = None
    for timestamp, price, _ in historical_prices:
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
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', ''))
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)  # Hacer offset-naive
            price = float(data['price'])
            # Hash rate ya está en TH/s desde el productor
            hash_rate = float(data['hash_rate'])

            # Actualizar gráfico lineal con precio y hash_rate
            if price is not None and isinstance(price, float) and not (price != price or price < 1000 or price > 1000000):
                price_data.append((timestamp, price, hash_rate))
                if len(price_data) > MAX_POINTS:
                    price_data.pop(0)
                price_data.sort(key=lambda x: x[0])
                print(f"Price data: {price_data[-1]}")

            # Gestionar velas (solo precio)
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
                    candle_data.sort(key=lambda x: x[0])
                    print(f"Candle data: {candle_data[-1]}")
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

# Calcular el rango inicial del eje Y secundario
hash_rates = [h for _, _, h in price_data]
min_hash_rate = min(hash_rates) if hash_rates else 0
max_hash_rate = max(hash_rates) if hash_rates else 700_000_000
hash_rate_range = [min_hash_rate * 0.9, max_hash_rate * 1.1]

line_chart_fig = go.Figure([
    go.Scatter(
        x=[t for t, _, _ in price_data],
        y=[p for _, p, _ in price_data],
        mode='lines',
        name='Precio',
        line=dict(color='blue')
    ),
    go.Scatter(
        x=[t for t, _, _ in price_data],
        y=[h for _, _, h in price_data],
        mode='lines',
        name='Hash Rate (TH/s)',
        line=dict(color='red'),
        yaxis='y2'
    )
]).update_layout(
    yaxis=dict(title='Precio (USD)'),
    yaxis2=dict(
        title='Hash Rate (TH/s)',
        overlaying='y',
        side='right',
        range=hash_rate_range
    )
)

app.layout = html.Div([
    html.H1("Bitcoin en tiempo real"),
    dcc.Graph(id='line-chart', figure=line_chart_fig),
    dcc.Graph(id='candlestick-chart', figure=go.Figure([go.Candlestick(
        x=[t for t, _, _, _, _ in candle_data],
        open=[o for _, o, _, _, _ in candle_data],
        high=[h for _, _, h, _, _ in candle_data],
        low=[l for _, _, _, l, _ in candle_data],
        close=[c for _, _, _, _, c in candle_data],
        name='Velas'
    )])),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Actualiza cada 1 segundo
        n_intervals=0
    )
])

# Callback para actualizar los datos del gráfico
@app.callback(
    [Output('line-chart', 'extendData'), Output('candlestick-chart', 'extendData')],
    Input('interval-component', 'n_intervals')
)
def update_graphs(n):
    global last_price_update, last_candle_update

    # Nuevos datos para el gráfico lineal (precio y hash_rate)
    new_line_data = [dict(x=[[]], y=[[]]), dict(x=[[]], y=[[]])]
    if len(price_data) > last_price_update:
        new_timestamps, new_prices, new_hash_rates = zip(*price_data[last_price_update:])
        new_line_data = [
            dict(x=[list(new_timestamps)], y=[list(new_prices)]),  # Traza 1: precio
            dict(x=[list(new_timestamps)], y=[list(new_hash_rates)])  # Traza 2: hash_rate
        ]
        last_price_update = len(price_data)
        print(f"Nuevos puntos lineales: {len(new_timestamps)}")

    # Nuevos datos para el gráfico de velas
    new_candle_data = dict(x=[[]], open=[[]], high=[[]], low=[[]], close=[[]])
    if len(candle_data) > last_candle_update:
        new_timestamps, new_opens, new_highs, new_lows, new_closes = zip(*candle_data[last_candle_update:])
        new_candle_data = dict(
            x=[list(new_timestamps)],
            open=[list(new_opens)],
            high=[list(new_highs)],
            low=[list(new_lows)],
            close=[list(new_closes)]
        )
        last_candle_update = len(candle_data)
        print(f"Nuevas velas: {len(new_timestamps)}")

    return (
        new_line_data, [0, 1]  # Actualizar ambas trazas
    ), (
        new_candle_data, [0]  # Actualizar la traza de velas
    )

# Callback para actualizar el rango del eje Y secundario
@app.callback(
    Output('line-chart', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('line-chart', 'figure')
)
def update_yaxis_range(n, current_figure):
    # Calcular el nuevo rango del eje Y secundario
    hash_rates = [h for _, _, h in price_data]
    min_hash_rate = min(hash_rates) if hash_rates else 0
    max_hash_rate = max(hash_rates) if hash_rates else 700_000_000
    hash_rate_range = [min_hash_rate * 0.9, max_hash_rate * 1.1]

    # Actualizar solo el layout del gráfico, preservando los datos y el zoom
    updated_figure = go.Figure(current_figure)
    updated_figure.update_layout(
        yaxis=dict(title='Precio (USD)'),
        yaxis2=dict(
            title='Hash Rate (TH/s)',
            overlaying='y',
            side='right',
            range=hash_rate_range
        )
    )
    return updated_figure

if __name__ == '__main__':
    app.run(debug=True)