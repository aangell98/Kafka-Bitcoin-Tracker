# Kafka Bitcoin Tracker

![Estado del proyecto](https://img.shields.io/badge/Estado-En%20desarrollo-yellow)
![Versión](https://img.shields.io/badge/Versión-0.1.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

## Descripción
**Kafka Bitcoin Tracker** es un proyecto desarrollado como parte de la asignatura *Gestión de Datos* del Grado en Ingeniería Informática en la Facultad de Ciencias Sociales de Talavera de la Reina. Su objetivo es visualizar en tiempo real la evolución del precio de Bitcoin (en USD) y el hash rate de la red Bitcoin, utilizando Apache Kafka para transmitir datos y gráficos interactivos en Python para su representación.

Esta versión inicial (`v0.1.0`) cumple con los requisitos básicos de la práctica, mostrando un gráfico de velas para el precio y una línea para el hash rate, pero aún está en desarrollo y no es una versión estable (1.0). Consulta las release notes de la version para mas información

---

## Características principales
- **Transmisión en tiempo real**: Datos enviados y recibidos mediante Kafka cada segundo.
- **Fuentes de datos**:
  - Precio de Bitcoin: WebSocket de CoinCap (`wss://ws.coincap.io/prices?assets=bitcoin`).
  - Hash rate: API REST de Blockchain.info (`https://api.blockchain.info/stats`), actualizado cada 60 segundos.
- **Visualización**:
  - Gráfico de velas para el precio de Bitcoin (Open, High, Low, Close) con intervalos de 1 minuto.
  - Vela en formación actualizada en tiempo real con cada nuevo precio.
  - Línea superpuesta para el hash rate en un eje Y secundario.
- **Límite de datos**: Hasta 10,000 puntos (~166 horas con intervalos de 1 minuto).

---

## Requisitos
- **Sistema operativo**: Windows (probado), Linux o macOS (debería ser compatible con ajustes mínimos).
- **Dependencias externas**:
  - Apache Kafka y Zookeeper instalados (versión recomendada: 3.9.0).
  - Python 3.7 o superior.
- **Librerías de Python**: Ver `requirements.txt`.

---

## Instalación

### 1. Configurar Kafka
1. Descarga Kafka desde [Apache Kafka Downloads](https://dlcdn.apache.org/kafka/3.9.0/kafka_2.13-3.9.0.tgz).
2. Descomprime el archivo y navega al directorio.
3. Inicia Zookeeper en una terminal:
   ```bash
   .\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
   ```
4. Inicia el servidor Kafka en otra terminal:
   ```bash
   .\bin\windows\kafka-server-start.bat .\config\server.properties
   ```
5. Crea el topic `bitcoin_data`:
   ```bash
   .\bin\windows\kafka-topics.bat --create --topic bitcoin_data --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   ```

### 2. Instalar dependencias de Python
1. Clona este repositorio:
   ```bash
   git clone https://github.com/<tu-usuario>/kafka-bitcoin-tracker.git
   cd kafka-bitcoin-tracker
   ```
2. Instala las librerías requeridas:
   ```bash
   pip install -r requirements.txt
   ```

---

## Uso
1. Asegúrate de que Zookeeper y Kafka estén corriendo.
2. Ejecuta el productor en una terminal:
   ```bash
   python producer.py
   ```
3. Ejecuta el consumidor en otra terminal para visualizar los datos:
   ```bash
   python consumer.py
   ```
4. Observa el gráfico en tiempo real que muestra las velas de precio y la línea de hash rate.

---

## Estructura del proyecto
- `producer.py`: Script que obtiene y envía datos a Kafka.
- `consumer.py`: Script que lee datos de Kafka y genera la visualización.
- `requirements.txt`: Lista de dependencias de Python.
- `RELEASE_NOTES.md`: Notas de la versión actual.

---

## Estado actual y limitaciones
Este proyecto está en desarrollo (versión `0.1.0`). Algunas limitaciones incluyen:
- El hash rate se actualiza cada 60 segundos, no en tiempo real completo.
- Posible ralentización del gráfico con grandes volúmenes de datos.
- Falta de manejo robusto de errores (por ejemplo, reconexión al WebSocket).

---

## Licencia
Este proyecto está bajo la [Licencia MIT](LICENSE).

---

## Créditos
- Desarrollado por el equipo de *Gestión de Datos* con apoyo de **Grok 3**.
- Basado en la práctica propuesta por **Ricardo Pérez del Castillo**.