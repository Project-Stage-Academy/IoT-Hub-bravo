# Kafka message broker

Kafka is used as a **durable message buffer** and **decoupling layer** 
between telemetry ingestion (MQTT/HTTP) and downstream processing 
(validation, storage, rules, realtime streaming).

Instead of processing telemetry synchronously(or triggering one background 
job per message), services publish telemetry events to Kafka topics. Independent 
consumers can then process the stream at their own pace, scale horizontally, 
and be deployed/updated without touching ingestion.

## Concepts

- **Topic**: a named stream of messages (e.g. `telemetry.raw`).
- **Producer**: publishes messages to a topic.
- **Consumer**: reads messages from a topic.
- **Consumer group** (`group.id`): controls scaling and fan-out.
  - Different group ids → each group receives **all** messages (fan-out).
  - Same group id across multiple instances → messages are **load-balanced** between instances.
- **Key**: used for partitioning.

## Topics and routing

Current topic convention:

- `telemetry.raw` — raw telemetry events from ingestion (MQTT/HTTP). Primary entry point for downstream.
- `telemetry.clean` — validated/normalized telemetry (output of validator).
- `telemetry.dlq` — invalid telemetry.

## Producer

`KafkaProducer` is a wrapper around `confluent-kafka` producer:
- encodes payload to UTF-8 JSON, 
- supports optional key, 
- uses non-blocking `poll()` to process delivery callbacks, 
- logs delivery failures, 
- includes retry/throughput defaults via `ProducerConfig`, 
- provides `flush()` for graceful shutdown.

### Default producer behavior

Producer is configured for reliability and throughput (see ProducerConfig):
- `acks=all` — waits for broker acknowledgment, 
- `enable.idempotence=true` — reduces duplicates during retries, 
- `retries>0` — retries transient broker/network failures, 
- `linger.ms` and `compression` — improves throughput by batching/compressing messages, 
- bounded producer queue — if local queue is full, producer may drop messages.

### Usage example

```python
from producers.config import ProducerConfig
from producers.kafka_producer import KafkaProducer

producer = KafkaProducer(
    config=ProducerConfig(),
    topic='telemetry.raw',
)

payload = {
    'schema_version': 1,
    'device': 'DEV-01',
    'metrics': {
        'humidity': 20,
        'temperature': 20,
    },
    'ts': '2026-02-20 22:45'
}
producer.produce(payload, key=payload['device'])

producer.flush()
```

## Consumer

`KafkaConsumer` is a wrapper around `confluent-kafka` consumer:
- subscribes to one or more topics, 
- supports single-message or batch consumption, 
- optionally decodes payload to JSON, 
- calls a provided handler (`handler.handle(payload)`), 
- supports auto-commit or manual commit, 
- handles SIGINT/SIGTERM for graceful shutdown.

### Batch consumption
If `consume_batch=True`, the consumer collects up to `batch_max_size` messages per 
iteration and forwards a single list to the handler. This is useful for high-throughput 
processing and downstream batch inserts.

### Graceful shutdown (`stop()`)
To stop the loop gracefully, call `consumer.stop()`. The `start()` loop will exit
after the current poll/consume iteration completes, and the underlying Kafka
consumer will be closed in `start()`'s `finally` block.

### Usage example

```python
import signal

from consumers.config import ConsumerConfig
from consumers.kafka_consumer import KafkaConsumer

class PrintHandler:
    def handle(self, payload):
        print(payload)

consumer = KafkaConsumer(
    config=ConsumerConfig(),
    topics=['telemetry.raw'],
    handler=PrintHandler(),
    consume_timeout=1.0,
    decode_json=True,
    consume_batch=True,
    batch_max_size=100,
)

# Register graceful shutdown
signal.signal(signal.SIGTERM, consumer.stop)
signal.signal(signal.SIGINT, consumer.stop)

consumer.start()
```


### Adding a new consumer service to docker-compose

- Create a module (example): `consumers/telemetry_raw_logger.py`
- Add a dedicated service to `docker-compose.yml`:

```yaml
telemetry-raw-logger:
  <<: *django_base
  image: iot-hub-telemetry-raw-logger
  container_name: telemetry-raw-logger
  command: ["python", "-m", "consumers.telemetry_raw_logger"]
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    KAFKA_GROUP_ID: telemetry-raw-logger
  depends_on:
    kafka:
      condition: service_healthy
```

## Kafka UI

Kafka UI is a web interface for convenient viewing of Kafka without CLI.

It is useful for:
- viewing **topics** (partitions, configs, retention),
- viewing **consumer groups** and **lag**,
- viewing **messages** in a topic,
- checking that producers/consumers are actually working.

Kafka UI is available at:
- `http://localhost:8080`
