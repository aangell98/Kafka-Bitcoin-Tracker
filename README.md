# Kafka-Bitcoin-Tracker
A real-time Bitcoin price and hash rate visualizer using Apache Kafka and Python.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Start ZooKeeper: `bin\windows\zookeeper-server-start.bat config\zookeeper.properties`
3. Start Kafka: `bin\windows\kafka-server-start.bat config\server.properties`
4. Create topic: `bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --create --topic BitcoinData --partitions 1 --replication-factor 1`
5. Run the producer: `python producer.py`
6. Run the consumer: `streamlit run consumer.py`

## APIs Used
- **Binance**: Real-time Bitcoin price (BTC/USDT)
- **Blockchain**: Bitcoin network hash rate
