import logging
import os
import signal
import sys

import django
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from apps.rules.consumers.event_db_handler import EventDBHandler # noqa: E402

TOPIC = config('KAFKA_TOPIC_RULE_EVENTS', default='rules.events.triggered')
GROUP_ID = config('KAFKA_GROUP_EVENT_DB_WRITER', default='event-db-writer-group')

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    consumer_config = ConsumerConfig(
        group_id=GROUP_ID,
        enable_auto_commit=False
    )

    logger.info(f"Starting Event DB Consumer... Group: {GROUP_ID}, Topic: {TOPIC}")

    consumer = KafkaConsumer(
        config=consumer_config,
        topics=[TOPIC],
        handler=EventDBHandler(),
        decode_json=True,
        consume_batch=True,
        batch_max_size=50,
    )

    def handle_shutdown(signum, frame):
        logger.warning('Received shutdown signal. Stopping consumer gracefully...')
        consumer.stop()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        consumer.start()
    except Exception as e:
        logger.error('Consumer crashed with exception: %s', e)
        sys.exit(1)

if __name__ == "__main__":
    main()