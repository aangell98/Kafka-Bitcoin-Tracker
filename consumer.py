import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
from kafka import KafkaConsumer
import json
import pandas as pd
from collections import deque
import threading
import requests
from datetime import datetime, timedelta

# Configuración del Consumer de Kafka
consumer = KafkaConsumer(
    'BitcoinData',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    consumer_timeout_ms=1000
)

# Buffer para almacenar datos
max_points = 10000
data_buffer = deque(maxlen=max_points)

# Función para obtener datos históricos de precios de Binance
def get_historical_prices(symbol="BTCUSDT", interval="1m", days=7):
    url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    all_data = []
    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000
        }
        response = requests.get(url, params=params)
        data = response.json()
        if not data:
            break
        all_data.extend(data)
        start_time = data[-1][6] + 1
    df = pd.DataFrame(all_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["close_time"], unit='ms')
    df["price"] = df["close"].astype(float)
    return df[["timestamp", "price"]]

# Función para obtener datos históricos de hash rate
def get_historical_hash_rate(days=7):
    url = f"https://api.blockchain.info/charts/hash-rate?timespan={days}days&format=json"
    response = requests.get(url)
    data = response.json()
    values = data["values"]
    df = pd.DataFrame(values)
    df["timestamp"] = pd.to_datetime(df["x"], unit='s')
    df["hash_rate"] = df["y"] / 1e6  # Convertir a TH/s
    df = df.set_index("timestamp").resample("D").last().reset_index()
    return df[["timestamp", "hash_rate"]]

# Precargar datos históricos
historical_prices = get_historical_prices(days=7)
historical_hash_rate = get_historical_hash_rate(days=7)

historical_data = historical_prices.copy()
historical_data["date"] = historical_data["timestamp"].dt.date
historical_hash_rate["date"] = historical_hash_rate["timestamp"].dt.date
historical_data = historical_data.merge(historical_hash_rate[["date", "hash_rate"]], on="date", how="left")
historical_data["hash_rate"] = historical_data["hash_rate"].ffill()
historical_list = historical_data[["timestamp", "price", "hash_rate"]].to_dict(orient="records")

data_buffer.extend([{
    "timestamp": row["timestamp"].isoformat(),
    "price": row["price"],
    "hash_rate": row["hash_rate"]
} for row in historical_list[-max_points:]])

print(f"Buffer inicializado con {len(data_buffer)} puntos históricos.")

# Leer datos de Kafka en tiempo real
def read_from_kafka():
    for message in consumer:
        data = message.value
        data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace("Z", "")).isoformat()
        data_buffer.append(data)

# Iniciar Kafka en un hilo separado
kafka_thread = threading.Thread(target=read_from_kafka, daemon=True)
kafka_thread.start()

# Inicializar Dash
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Monitor de Bitcoin en Tiempo Real", style={'textAlign': 'center'}),
    dcc.Graph(id='live-graph'),
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
])

@app.callback(
    Output('live-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_graph(n):
    if not data_buffer:
        return go.Figure()

    df = pd.DataFrame(list(data_buffer))
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['price'],
        mode='lines',
        name='Precio (USD)',
        line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['hash_rate'],
        mode='lines',
        name='Hash Rate (TH/s)',
        line=dict(color='red'),
        yaxis='y2'
    ))
    fig.update_layout(
        title='Evolución del Precio de Bitcoin y Hash Rate',
        xaxis_title='Tiempo',
        yaxis_title='Precio (USD)',
        yaxis2=dict(title='Hash Rate (TH/s)', overlaying='y', side='right')
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True)