import logging
import os
import signal
from decouple import config
from typing import Any
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from common.redis_client import get_redis_client
from apps.rules.tasks import evaluate_rule
from apps.common.serializers import JSONSerializer

logger = logging.getLogger(__name__)

# kafka conf
TOPIC = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw') # change to telemetry.clean
CONSUME_TIMEOUT = config('KAFKA_CONSUMER_CONSUME_TIMEOUT', default=1.0, cast=float)
DECODE_JSON = config('KAFKA_CONSUMER_DECODE_JSON', default=True, cast=bool)
CONSUME_BATCH = config('KAFKA_CONSUMER_CONSUME_BATCH', default=True, cast=bool)
BATCH_MAX_SIZE = config('KAFKA_CONSUMER_BATCH_MAX_SIZE', default=100, cast=int)

redis_client = get_redis_client()


class RuleTelemetryRawSerializer(JSONSerializer):
    REQUIRED_FIELDS = {
        "ts": str,
        "device": str,
        "metrics": dict,
    }
    OPTIONAL_FIELDS = {}
    STRICT = True

    def _validate_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        ts_raw = data["ts"]
        ts = parse_datetime(ts_raw)
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts)
        data["ts"] = ts
        return data


class RuleEvalHandler:
    def __init__(self, rule_runner):
        self.rule_runner = rule_runner
        self.serializer = RuleTelemetryRawSerializer()

    def handle(self, payload):
        if isinstance(payload, list):
            for item in payload:
                self._handle_single(item)
        else:
            self._handle_single(payload)

    def _handle_single(self, item):
        validated = self.serializer._validate(item)
        if not validated:
            logger.warning("Invalid telemetry payload: %s", item)
            return

        ts = validated["ts"]
        device_serial_id = validated["device"]
        metrics = validated["metrics"]

        for metric_type, value in metrics.items():
            key = f"telemetry:{device_serial_id}:{metric_type}"
            member = f"{ts.timestamp()}:{value}"
            redis_client.zadd(key, {member: ts.timestamp()})

            telemetry = {
                "device_serial_id": device_serial_id,
                "metric_type": metric_type,
                "value": value,
                "ts": ts.isoformat()
            }

            self.rule_runner.delay(telemetry)


def main():
    """Starts the Kafka rule evaluation consumer"""
    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[TOPIC],
        handler=RuleEvalHandler(evaluate_rule),
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

