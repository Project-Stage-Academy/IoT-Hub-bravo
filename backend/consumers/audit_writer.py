import os
import logging
import signal
from typing import Any

import django
from decouple import config

from apps.audit.serializers import AuditLogBatchSerializer
from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from utils.logging import setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.audit.services.audit_log_services import audit_log_create_batch  # noqa

TOPIC = config('KAFKA_TOPIC_AUDIT_RECORDS', default='audit.records')
CONSUME_TIMEOUT = config('KAFKA_CONSUMER_CONSUME_TIMEOUT', default=1.0, cast=float)
DECODE_JSON = config('KAFKA_CONSUMER_DECODE_JSON', default=True, cast=bool)
CONSUME_BATCH = config('KAFKA_CONSUMER_CONSUME_BATCH', default=True, cast=bool)
BATCH_MAX_SIZE = config('KAFKA_CONSUMER_BATCH_MAX_SIZE', default=100, cast=int)

logger = logging.getLogger(__name__)


class AuditRecordWriter:
    def handle(self, payload: Any) -> None:
        if isinstance(payload, dict):
            payload = [payload]
        elif isinstance(payload, list):
            pass
        else:
            logger.error(f'payload must be of type dict or list, got {type(payload).__name__}')
            return

        s = AuditLogBatchSerializer(payload)
        if not s.is_valid() and not s.valid_items:
            logger.warning('Telemetry ingestion task rejected: errors=%s', len(s.errors))
            return

        audit_log_create_batch(s.valid_items)


def main():
    setup_logging()

    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[TOPIC],
        handler=AuditRecordWriter(),
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
