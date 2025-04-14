# Kafka Bitcoin Tracker

![Estado del proyecto](https://img.shields.io/badge/Estado-Completado-green)
![Versión](https://img.shields.io/badge/Versión-1.0.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)


Este proyecto es un dashboard en tiempo real que muestra el precio de Bitcoin (obtenido desde Binance vía WebSocket) y el hashrate de la red (desde Blockchain.info), utilizando Kafka como sistema de mensajería y Dash para la visualización. El sistema consta de un productor (`producer.py`) que envía datos a Kafka y un consumidor (`consumer.py`) que los lee y genera gráficos interactivos.

## Video resumen de funcionalidades de la APP

https://pruebasaluuclm-my.sharepoint.com/:v:/r/personal/angelluis_lara_alu_uclm_es/Documents/Practica5.mp4?csf=1&web=1&e=auShDV&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJTdHJlYW1XZWJBcHAiLCJyZWZlcnJhbFZpZXciOiJTaGFyZURpYWxvZy1MaW5rIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXcifX0%3D

## Requisitos previos

- **Python 3.8+**: Necesario para ejecutar los scripts.
- **Kafka**: Instalado y configurado (descarga desde [Apache Kafka](https://kafka.apache.org/downloads)).
- **Dependencias de Python**: Instálalas con:
  ```
  pip install -r requirements.txt
  ```
  Contenido sugerido para `requirements.txt`:
  ```
  websocket-client
  requests
  kafka-python
  pandas
  dash
  plotly
  python-dotenv
  ```

## Estructura del proyecto

```
Kafka-Bitcoin-Tracker/
├── producer.py          # Script que produce datos de precio y hashrate
├── consumer.py          # Script que consume datos y muestra el dashboard
├── start_all.bat        # Script para Windows que inicia todos los servicios
├── Makefile             # Script para Linux/Mac que inicia todos los servicios
├── .env.template        # Archivo de configuración de variables de entorno
├── LICENSE              # Licencia
├── .gitignore           # Archivos ignorados
└── README.md            # Este archivo
```

## Configuración

### 1. Configurar Kafka
Descarga e instala Kafka desde [Apache Kafka](https://kafka.apache.org/downloads). Asegúrate de que Zookeeper y Kafka puedan ejecutarse desde el directorio especificado (por ejemplo, `./kafka`).

### 2. Configurar el archivo `.env`
Cambia el nombre del archivo .env.template y elimina el ".template" en el directorio raíz del proyecto y modifica las variables segun tu configuracion

- **`KAFKA_DIR`**: Ruta al directorio donde está instalado Kafka (por ejemplo, `.\kafka` o `C:\kafka`).
- **`ZOOKEEPER_START` y `KAFKA_START`**: Ajusta según tu sistema operativo (`.bat` para Windows, `.sh` para Linux/Mac).
- **`PRODUCER_PATH` y `CONSUMER_PATH`**: Rutas a los scripts Python, relativas al directorio del proyecto.

### 3. Instalar dependencias
Ejecuta:
```bash
pip install -r requirements.txt
```

## Ejecución

El proyecto incluye scripts para automatizar el inicio de Zookeeper, Kafka, el productor y el consumidor. Sigue las instrucciones según tu sistema operativo.

### Windows (usando `start_all.bat`)

1. Asegúrate de que el `.env` esté configurado correctamente.
2. Ejecuta el script desde el directorio raíz del proyecto:
   ```bash
   ./start_all.bat
   ```
3. Esto abrirá cuatro ventanas:
   - Zookeeper
   - Kafka Server
   - Producer
   - Consumer (abre el dashboard en `http://127.0.0.1:8050/`)

4. Para detener, cierra las ventanas manualmente o usa `Ctrl+C` en cada una.

### Linux/Mac (usando `Makefile`)

1. Asegúrate de que el `.env` esté configurado con las rutas correctas para Linux/Mac (`.sh` en lugar de `.bat`).
2. Ejecuta:
   ```bash
   make start
   ```
3. Esto inicia todos los servicios en segundo plano:
   - Zookeeper
   - Kafka Server
   - Producer
   - Consumer (abre el dashboard en `http://127.0.0.1:8050/`)

4. Para detener:
   ```bash
   make stop
   ```

#### Contenido del `Makefile`
```makefile
include .env

start: zookeeper kafka producer consumer

zookeeper:
	$(ZOOKEEPER_START) $(ZOOKEEPER_CONFIG) &

kafka:
	$(KAFKA_START) $(KAFKA_CONFIG) &

producer:
	python $(PRODUCER_PATH) &

consumer:
	python $(CONSUMER_PATH) &

stop:
	pkill -f zookeeper
	pkill -f kafka
	pkill -f producer.py
	pkill -f consumer.py
```

## Uso del dashboard

- **Gráfico combinado**: Muestra el precio de Bitcoin (en USD) y el hashrate (en TH/s) en tiempo real.
- **Gráfico de velas**: Muestra velas de 1 minuto (configurable en `CANDLE_INTERVAL`) con precios de apertura, máximo, mínimo y cierre. Las velas son verdes para movimientos alcistas y rojas para bajistas.
- **Interactividad**: Usa el zoom, desplazamiento y la barra deslizante para explorar los datos.
- **URL**: Abre `http://127.0.0.1:8050/` en tu navegador tras iniciar el consumidor.

## Notas adicionales

- **Errores comunes**:
  - Si Kafka no inicia, verifica que `KAFKA_DIR` y las rutas en `.env` sean correctas.
  - Asegúrate de que el puerto `9092` (o el configurado en `KAFKA_BOOTSTRAP_SERVERS`) esté libre.
- **Personalización**: Modifica `CANDLE_INTERVAL` en `.env` para cambiar el intervalo de las velas (en segundos).
- **Logs**: Los scripts imprimen mensajes en consola para monitorear precios, hashrate y envío de datos.
