# Cargar variables desde .env
include .env

# Comandos para iniciar servicios
start: zookeeper kafka producer consumer

zookeeper:
	$(ZOOKEEPER_START) $(ZOOKEEPER_CONFIG) &

kafka:
	$(KAFKA_START) $(KAFKA_CONFIG) &

producer:
	python $(PRODUCER_PATH) &

consumer:
	python $(CONSUMER_PATH) &

# Detener servicios (opcional)
stop:
	pkill -f zookeeper
	pkill -f kafka
	pkill -f producer.py
	pkill -f consumer.py