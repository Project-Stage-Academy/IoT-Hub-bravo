import logging
import os
import signal

import django
from decouple import config

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from consumers.message_handlers import CeleryPayloadHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.devices.tasks import ingest_telemetry_payload  # noqa

# TODO: switch topic to KAFKA_TOPIC_TELEMETRY_CLEAN (telemetry.clean)
TOPIC = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')
CONSUME_TIMEOUT = config('KAFKA_CONSUMER_CONSUME_TIMEOUT', default=1.0, cast=float)
DECODE_JSON = config('KAFKA_CONSUMER_DECODE_JSON', default=True, cast=bool)
CONSUME_BATCH = config('KAFKA_CONSUMER_CONSUME_BATCH', default=True, cast=bool)
BATCH_MAX_SIZE = config('KAFKA_CONSUMER_BATCH_MAX_SIZE', default=100, cast=int)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
    )
    logging.getLogger().setLevel(logging.INFO)


def main():
    """
    Kafka consumer entrypoint.

    This consumer subscribes to telemetry.raw and:
        1) polls Kafka for messages in batches,
        2) decodes messages to JSON,
        3) forwards payloads to a Celery task,
        4) commits Kafka offsets after the handler call succeeds.

    The Celery task is responsible for:
        - serialization,
        - validation & normalization,
        - writing data to DB.

    TODO
        - Implement a validation stage that publishes validated telemetry
        into telemetry.clean topic.
        - Update this consumer to subscribe to telemetry.clean instead of
        telemetry.raw and perform only DB write with minimal transformation.
    """
    setup_logging()

    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[TOPIC],
        handler=CeleryPayloadHandler(ingest_telemetry_payload),
        consume_timeout=CONSUME_TIMEOUT,
        decode_json=DECODE_JSON,
        consume_batch=CONSUME_BATCH,
        batch_max_size=BATCH_MAX_SIZE,
    )

    signal.signal(signal.SIGTERM, consumer.stop)
    signal.signal(signal.SIGINT, consumer.stop)

    consumer.start()


if __name__ == '__main__':
    main()
