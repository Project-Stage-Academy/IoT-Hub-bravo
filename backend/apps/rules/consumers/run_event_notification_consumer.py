import logging
import os
import signal
import sys

import django
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from consumers.kafka_consumer import KafkaConsumer  # noqa: E402
from consumers.config import ConsumerConfig  # noqa: E402

from apps.rules.consumers.event_notification_handler import EventNotificationHandler  # noqa: E402

TOPIC = config('KAFKA_TOPIC_RULE_EVENTS', default='rules.events.triggered')
GROUP_ID = config('KAFKA_GROUP_EVENT_NOTIFICATION', default='event-notification-group')


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s %(message)s', force=True
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    consumer_config = ConsumerConfig(group_id=GROUP_ID, enable_auto_commit=False)

    logger.info(f"Starting Notification Consumer... Group: {GROUP_ID}, Topic: {TOPIC}")

    consumer = KafkaConsumer(
        config=consumer_config,
        topics=[TOPIC],
        handler=EventNotificationHandler(),
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


if __name__ == '__main__':
    main()
