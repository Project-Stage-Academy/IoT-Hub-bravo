import logging

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig
from mqtt_adapter.config import MqttConfig
from mqtt_adapter.mqtt_client import run_mqtt_client
from mqtt_adapter.message_handlers import KafkaProducerMessageHandler

topic = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')


def setup_logging() -> None:
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    setup_logging()

    kafka_producer = KafkaProducer(
        config=ProducerConfig(),
        topic=topic,
    )

    message_handler = KafkaProducerMessageHandler(
        producer=kafka_producer,
        key_field='device',
    )

    run_mqtt_client(
        config=MqttConfig(),
        handler=message_handler,
    )

    kafka_producer.flush()


if __name__ == '__main__':
    main()
