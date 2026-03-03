import logging
import os
import signal

import django
from decouple import config

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.rules import tasks  # noqa: E402

logger = logging.getLogger(__name__)


class NotifyEventHandler:
    def handle(self, payload: dict) -> None:
        try:
            event_id = int(payload.get('event_id'))
        except Exception:
            logger.warning('Received rule event without valid event_id: %s', payload)
            return

        try:
            tasks.notify_event.delay(event_id)
            logger.info('Enqueued notify_event for %s', event_id)
        except Exception:
            logger.exception('Failed to enqueue notify_event task')


TOPIC = config('KAFKA_TOPIC_RULE_EVENTS', default='events.rule_triggered')
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
    setup_logging()

    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[TOPIC],
        handler=NotifyEventHandler(),
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
