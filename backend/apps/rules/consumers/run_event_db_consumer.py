import logging
import os
import signal

import django
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from consumers.kafka_consumer import KafkaConsumer  # noqa: E402
from consumers.config import ConsumerConfig  # noqa: E402
from apps.rules.consumers.event_db_handler import EventDBHandler  # noqa: E402

INTERNAL_EVENTS = config('KAFKA_TOPIC_RULE_EVENTS', default='rules.events.triggered')
EXTERNAL_EVENTS = config('KAFKA_TOPIC_RULE_EXTERNAL_EVENTS', default='rules.events.external')
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

    consumer_config = ConsumerConfig(group_id=GROUP_ID, enable_auto_commit=False)

    logger.info(
        f"Starting Event DB Consumer... Group: {GROUP_ID}, Topic: {INTERNAL_EVENTS}, {EXTERNAL_EVENTS}"
    )

    consumer = KafkaConsumer(
        config=consumer_config,
        topics=[INTERNAL_EVENTS, EXTERNAL_EVENTS],
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

    consumer.start()


if __name__ == "__main__":
    main()
