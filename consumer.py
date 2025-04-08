import json
from kafka import KafkaConsumer
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
from collections import deque
import threading

# Configuración del Consumer de Kafka
consumer = KafkaConsumer(
    'BitcoinData',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='latest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Buffer para datos (máximo 10,000 puntos)
MAX_POINTS = 10000
data_buffer = deque(maxlen=MAX_POINTS)

# Función para leer datos de Kafka y actualizar el buffer
def update_data():
    for message in consumer:
        data = message.value
        data_buffer.append({
            'timestamp': data['timestamp'],
            'price': data['price'],
            'hash_rate': data['hash_rate']
        })

# Iniciar la lectura de Kafka en un hilo separado
kafka_thread = threading.Thread(target=update_data, daemon=True)
kafka_thread.start()

# Inicializar la aplicación Dash
app = Dash(__name__)

# Diseño de la interfaz
app.layout = html.Div(
    style={'backgroundColor': '#1a1a1a', 'padding': '20px', 'fontFamily': 'Arial'},
    children=[
        html.H1(
            "Bitcoin Price & Hashrate Dashboard",
            style={'textAlign': 'center', 'color': '#ffffff'}
        ),
        dcc.Graph(id='combined-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1*1000,  # Actualizar cada 1 segundo
            n_intervals=0
        )
    ]
)

# Callback para actualizar el gráfico combinado
@app.callback(
    Output('combined-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    # Convertir buffer a DataFrame
    df = pd.DataFrame(list(data_buffer))

    # Si no hay datos, devolver gráfico vacío
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template='plotly_dark',
            title="Esperando datos...",
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Valor'}
        )
        return empty_fig

    # Crear gráfico combinado
    fig = go.Figure()

    # Línea de Precio (eje Y izquierdo)
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['price'],
            mode='lines',
            name='Precio (USD)',
            line=dict(color='#00cc96', width=2),
            yaxis='y1'
        )
    )

    # Línea de Hashrate (eje Y derecho)
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['hash_rate'],
            mode='lines',
            name='Hashrate (TH/s)',
            line=dict(color='#ffcc00', width=2),
            yaxis='y2'
        )
    )

    # Configurar el layout con dos ejes Y
    fig.update_layout(
        title='Bitcoin Price vs Hashrate en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis=dict(
            title='Precio (USD)',
            titlefont=dict(color='#00cc96'),
            tickfont=dict(color='#00cc96'),
            side='left'
        ),
        yaxis2=dict(
            title='Hashrate (TH/s)',
            titlefont=dict(color='#ffcc00'),
            tickfont=dict(color='#ffcc00'),
            overlaying='y',
            side='right'
        ),
        template='plotly_dark',
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='#ffffff'),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0)'),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)