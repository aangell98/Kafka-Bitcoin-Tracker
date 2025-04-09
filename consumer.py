import json
from kafka import KafkaConsumer
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objs as go
from collections import deque
import threading
import time
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env
load_dotenv()

# Configura el consumidor de Kafka para leer datos del tópico definido en .env
consumer = KafkaConsumer(
    os.getenv('KAFKA_TOPIC'),
    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Buffers para datos en tiempo real y velas (máximo definido en .env)
MAX_POINTS = int(os.getenv('MAX_POINTS'))
data_buffer = deque(maxlen=MAX_POINTS)
last_update_time = time.time()
candle_buffer = deque(maxlen=MAX_POINTS)
current_candle = None
candle_interval = int(os.getenv('CANDLE_INTERVAL'))  # Intervalo de velas desde .env

# Procesa datos en velas de 1 minuto
def process_candle_data(data):
    global current_candle, candle_buffer
    timestamp = pd.to_datetime(data['timestamp'])
    price = data['price']
    if current_candle is None:
        current_candle = {
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'start_time': timestamp,
            'end_time': timestamp + pd.Timedelta(seconds=candle_interval)
        }
    else:
        current_candle['high'] = max(current_candle['high'], price)
        current_candle['low'] = min(current_candle['low'], price)
        current_candle['close'] = price
        if timestamp >= current_candle['end_time']:
            candle_buffer.append({
                'timestamp': current_candle['start_time'],
                'open': current_candle['open'],
                'high': current_candle['high'],
                'low': current_candle['low'],
                'close': current_candle['close']
            })
            current_candle = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'start_time': timestamp,
                'end_time': timestamp + pd.Timedelta(seconds=candle_interval)
            }

# Lee datos de Kafka y actualiza buffers en un hilo separado
def update_data():
    global last_update_time
    for message in consumer:
        data = message.value
        data_buffer.append({
            'timestamp': data['timestamp'],
            'price': data['price'],
            'hash_rate': data['hash_rate']
        })
        process_candle_data(data)
        last_update_time = time.time()

kafka_thread = threading.Thread(target=update_data, daemon=True)
kafka_thread.start()

# Inicializa la aplicación Dash
app = Dash(__name__)

# Define el diseño del dashboard
app.layout = html.Div(
    style={
        'backgroundColor': '#1a1a1a',
        'padding': '30px',
        'fontFamily': 'Arial',
        'color': '#ffffff',
        'minHeight': '100vh'
    },
    children=[
        html.H1(
            "Precio del BitCoin & Hashrate Dashboard",
            style={
                'textAlign': 'center',
                'color': '#00cc96',
                'fontSize': '36px',
                'marginBottom': '20px'
            }
        ),
        html.Div(
            id='buffer-counter',
            style={
                'textAlign': 'center',
                'fontSize': '20px',
                'marginBottom': '30px',
                'color': '#ffcc00'
            }
        ),
        html.Div(
            [
                html.P(
                    "El hashrate mide la potencia computacional de la red Bitcoin en terahashes por segundo (TH/s). "
                    "Un valor más alto indica mayor seguridad y actividad minera.",
                    style={'fontSize': '14px', 'color': '#cccccc', 'marginBottom': '10px'}
                ),
                html.P(
                    "El gráfico de velas muestra el precio en intervalos de 1 minuto: apertura (open), máximo (high), "
                    "mínimo (low) y cierre (close), actualizándose en tiempo real. Usa el zoom, desplazamiento y la barra deslizante para explorar.",
                    style={'fontSize': '14px', 'color': '#cccccc'}
                )
            ],
            style={'textAlign': 'center', 'maxWidth': '800px', 'margin': '0 auto 30px'}
        ),
        dcc.Graph(id='combined-graph'),
        dcc.Graph(id='candle-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1*1000,
            n_intervals=0
        ),
        dcc.Store(id='combined-zoom-store', data={}),
        dcc.Store(id='candle-zoom-store', data={})
    ]
)

# Actualiza los gráficos y el contador en tiempo real
@app.callback(
    [Output('combined-graph', 'figure'),
     Output('candle-graph', 'figure'),
     Output('buffer-counter', 'children'),
     Output('combined-zoom-store', 'data'),
     Output('candle-zoom-store', 'data')],
    [Input('interval-component', 'n_intervals'),
     Input('combined-graph', 'relayoutData'),
     Input('candle-graph', 'relayoutData')],
    [State('combined-zoom-store', 'data'),
     State('candle-zoom-store', 'data')]
)
def update_graphs_and_counter(n, combined_relayout, candle_relayout, combined_zoom_store, candle_zoom_store):
    global last_update_time, current_candle
    df_line = pd.DataFrame(list(data_buffer))
    df_candle = pd.DataFrame(list(candle_buffer))
    buffer_size = len(data_buffer)

    counter_text = f"Puntos en el buffer: {buffer_size}/{MAX_POINTS}"
    if time.time() - last_update_time > 10:
        counter_text += " (Esperando datos...)"

    if df_line.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template='plotly_dark',
            title="Esperando datos...",
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Valor'}
        )
        return empty_fig, empty_fig, counter_text, {}, {}

    # Gráfico combinado de precio y hashrate
    fig_line = go.Figure()
    fig_line.add_trace(
        go.Scatter(
            x=df_line['timestamp'],
            y=df_line['price'],
            mode='lines',
            name='Precio (USD)',
            line=dict(color='#00cc96', width=2),
            yaxis='y1'
        )
    )
    fig_line.add_trace(
        go.Scatter(
            x=df_line['timestamp'],
            y=df_line['hash_rate'],
            mode='lines',
            name='Hashrate (TH/s)',
            line=dict(color='#ffcc00', width=2),
            yaxis='y2'
        )
    )
    fig_line.update_layout(
        title=dict(
            text='Precio del Bitcoin vs Hashrate en Tiempo Real',
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis_title='Tiempo',
        yaxis=dict(
            title=dict(
                text='Precio (USD)',
                font=dict(color='#00cc96')
            ),
            tickfont=dict(color='#00cc96'),
            side='left'
        ),
        yaxis2=dict(
            title=dict(
                text='Hashrate (TH/s)',
                font=dict(color='#ffcc00')
            ),
            tickfont=dict(color='#ffcc00'),
            overlaying='y',
            side='right'
        ),
        template='plotly_dark',
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='#ffffff'),
        legend=dict(
            x=0.01,
            y=1.1,
            bgcolor='rgba(0,0,0,0)',
            orientation='h'
        ),
        margin=dict(l=50, r=50, t=100, b=50),
        height=400,
        uirevision='combined',
        xaxis_rangeslider_visible=True,
        xaxis_rangeslider_thickness=0.05
    )
    if combined_relayout and 'xaxis.range[0]' in combined_relayout:
        fig_line.update_layout(
            xaxis_range=[combined_relayout.get('xaxis.range[0]'), combined_relayout.get('xaxis.range[1]')],
            yaxis_range=[combined_relayout.get('yaxis.range[0]'), combined_relayout.get('yaxis.range[1]')],
            yaxis2_range=[combined_relayout.get('yaxis2.range[0]'), combined_relayout.get('yaxis2.range[1]')]
        )
    elif combined_zoom_store:
        fig_line.update_layout(
            xaxis_range=[combined_zoom_store.get('xaxis.range[0]'), combined_zoom_store.get('xaxis.range[1]')],
            yaxis_range=[combined_zoom_store.get('yaxis.range[0]'), combined_zoom_store.get('yaxis.range[1]')],
            yaxis2_range=[combined_zoom_store.get('yaxis2.range[0]'), combined_zoom_store.get('yaxis2.range[1]')]
        )

    # Gráfico de velas de 1 minuto
    candle_fig = go.Figure()
    if not df_candle.empty:
        candle_fig.add_trace(
            go.Candlestick(
                x=df_candle['timestamp'],
                open=df_candle['open'],
                high=df_candle['high'],
                low=df_candle['low'],
                close=df_candle['close'],
                increasing_line_color='#00cc96',  # Verde para velas alcistas
                decreasing_line_color='#ff4444',  # Rojo para velas bajistas
                name='Velas Cerradas',
                opacity=1.0
            )
        )

    if current_candle is not None:
        candle_fig.add_trace(
            go.Candlestick(
                x=[current_candle['start_time']],
                open=[current_candle['open']],
                high=[current_candle['high']],
                low=[current_candle['low']],
                close=[current_candle['close']],
                increasing_line_color='#00cc96',  # Verde para vela en curso alcista
                decreasing_line_color='#ff4444',  # Rojo para vela en curso bajista
                name='Vela en Curso',
                opacity=0.6
            )
        )

    candle_fig.update_layout(
        title=dict(
            text='Precio de Bitcoin en Velas (1 minuto) - Tiempo Real',
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis_title='Tiempo',
        yaxis=dict(
            title=dict(
                text='Precio (USD)',
                font=dict(color='#00cc96')
            ),
            tickfont=dict(color='#00cc96')
        ),
        template='plotly_dark',
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='#ffffff'),
        margin=dict(l=50, r=50, t=100, b=50),
        height=400,
        showlegend=True,
        uirevision='candle',
        xaxis_rangeslider_visible=True,
        xaxis_rangeslider_thickness=0.05
    )
    if candle_relayout and 'xaxis.range[0]' in candle_relayout:
        candle_fig.update_layout(
            xaxis_range=[candle_relayout.get('xaxis.range[0]'), candle_relayout.get('xaxis.range[1]')],
            yaxis_range=[candle_relayout.get('yaxis.range[0]'), candle_relayout.get('yaxis.range[1]')]
        )
    elif candle_zoom_store:
        candle_fig.update_layout(
            xaxis_range=[candle_zoom_store.get('xaxis.range[0]'), candle_zoom_store.get('xaxis.range[1]')],
            yaxis_range=[candle_zoom_store.get('yaxis.range[0]'), candle_zoom_store.get('yaxis.range[1]')]
        )

    combined_zoom = combined_relayout if combined_relayout else combined_zoom_store
    candle_zoom = candle_relayout if candle_relayout else candle_zoom_store

    return fig_line, candle_fig, counter_text, combined_zoom, candle_zoom

# Inicia el servidor Dash
if __name__ == '__main__':
    app.run(debug=False)