import logging
import os
import signal
from decouple import config
from prometheus_client import Counter
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import django

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.common.redis_client import get_redis_client  # noqa
from apps.rules.tasks import evaluate_rule  # noqa


logger = logging.getLogger(__name__)
rule_eval_errors_total = Counter(
    "rule_eval_errors_total", "Number of telemetry payloads failed during rule evaluation"
)

# kafka conf
TOPIC = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')  # change to telemetry.clean
CONSUME_TIMEOUT = config('KAFKA_CONSUMER_CONSUME_TIMEOUT', default=1.0, cast=float)
DECODE_JSON = config('KAFKA_CONSUMER_DECODE_JSON', default=True, cast=bool)
CONSUME_BATCH = config('KAFKA_CONSUMER_CONSUME_BATCH', default=True, cast=bool)
BATCH_MAX_SIZE = config('KAFKA_CONSUMER_BATCH_MAX_SIZE', default=100, cast=int)

redis_client = get_redis_client()


class RuleEvalHandler:
    def __init__(self, rule_runner):
        self.rule_runner = rule_runner

    def handle(self, payload):
        if isinstance(payload, list):
            for item in payload:
                self._handle_single(item)
        else:
            self._handle_single(payload)

    def _handle_single(self, item):
        try:
            ts_raw = item.get("ts")
            ts = parse_datetime(ts_raw)
            if ts is None:
                logger.warning("Invalid timestamp received", extra={"timestamp": ts_raw})
                rule_eval_errors_total.inc()
                return

            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts)

            device_serial_id = item.get("device")

            for metric_type, value in item.get("metrics", {}).items():
                key = f"telemetry:{device_serial_id}:{metric_type}"

                if isinstance(value, dict) and "value" in value:
                    value_num = value.get("value")
                else:
                    value_num = value

                member = f"{ts.timestamp()}:{value_num}"
                redis_client.zadd(key, {member: ts.timestamp()})

                telemetry = {
                    "device_serial_id": device_serial_id,
                    "metric_type": metric_type,
                    "value": value_num,
                    "ts": ts_raw,
                }

                self.rule_runner.delay(telemetry)

        except Exception:
            logger.exception("Failed to process telemetry payload: %s", item)
            rule_eval_errors_total.inc()


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
