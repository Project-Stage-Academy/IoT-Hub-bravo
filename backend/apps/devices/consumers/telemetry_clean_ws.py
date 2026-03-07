import logging
import os
import signal

import django
from decouple import config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
django.setup()

from consumers.config import ConsumerConfig  
from consumers.kafka_consumer import KafkaConsumer  
from apps.devices.kafka_handlers.telemetry_clean_handler import WebSocketTelemetryCleanHandler  
logger = logging.getLogger(__name__)

TOPIC = config("KAFKA_TOPIC_TELEMETRY_CLEAN", default="telemetry.clean")
CONSUME_TIMEOUT = config("KAFKA_CONSUMER_CONSUME_TIMEOUT", default=1.0, cast=float)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def main() -> None:
    setup_logging()
    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[TOPIC],
        handler=WebSocketTelemetryCleanHandler(),
        consume_timeout=CONSUME_TIMEOUT,
        decode_json=True,
    )
    signal.signal(signal.SIGTERM, consumer.stop)
    signal.signal(signal.SIGINT, consumer.stop)
    logger.info("Starting telemetry.clean → WebSocket consumer...")
    consumer.start()


if __name__ == "__main__":
    main()
