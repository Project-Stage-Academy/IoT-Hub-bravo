import logging
import os

import django

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from consumers.message_handlers import CeleryPayloadHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.devices.tasks import ingest_telemetry_payload  # noqa


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
    )
    logging.getLogger().setLevel(logging.INFO)


def main():
    setup_logging()

    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=['telemetry.raw'],
        handler=CeleryPayloadHandler(ingest_telemetry_payload),
        consume_timeout=1.0,
        decode_json=True,
        consume_batch=True,
        batch_max_size=100,
    )
    consumer.start()


if __name__ == '__main__':
    main()
