import signal

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig
from mqtt_adapter.config import MqttConfig
from mqtt_adapter.mqtt_client import get_mqtt_client
from mqtt_adapter.message_handlers import KafkaProducerMessageHandler
from utils.logging import setup_logging

TOPIC = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')
KEY_FIELD = config('MQTT_PRODUCER_KEY_FIELD', default='device')


def main() -> None:
    setup_logging()

    kafka_producer = KafkaProducer(
        config=ProducerConfig(),
        topic=TOPIC,
    )

    message_handler = KafkaProducerMessageHandler(
        producer=kafka_producer,
        key_field=KEY_FIELD,
    )

    client = get_mqtt_client(
        config=MqttConfig(),
        handler=message_handler,
    )

    def _stop(*_):
        client.disconnect()
        kafka_producer.flush()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    client.loop_forever(retry_first_connection=True)


if __name__ == '__main__':
    main()
