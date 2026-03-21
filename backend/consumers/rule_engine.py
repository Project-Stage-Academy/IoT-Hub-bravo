import logging
import os
import signal
from decouple import config
from prometheus_client import Counter
import django

from apps.common.serializers.rule_engine_serializer import RuleEngineSerializer
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
CLEAN_TOPIC = config('KAFKA_TOPIC_TELEMETRY_CLEAN', default='telemetry.clean')
EXPIRED_TOPIC = config('KAFKA_TOPIC_TELEMETRY_EXPIRED', default='telemetry.expired')
CONSUME_TIMEOUT = config('KAFKA_CONSUMER_CONSUME_TIMEOUT', default=1.0, cast=float)
DECODE_JSON = config('KAFKA_CONSUMER_DECODE_JSON', default=True, cast=bool)
CONSUME_BATCH = config('KAFKA_CONSUMER_CONSUME_BATCH', default=True, cast=bool)
BATCH_MAX_SIZE = config('KAFKA_CONSUMER_BATCH_MAX_SIZE', default=100, cast=int)

# redis conf
TELEMETRY_KEY_TTL = config('TELEMETRY_KEY_TTL', default=3600, cast=int)
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
            serializer = RuleEngineSerializer(data=item)

            if not serializer.is_valid():
                logger.warning("Invalid telemetry payload", extra={"errors": serializer.errors})
                rule_eval_errors_total.inc()
                return
            validated = serializer.validated_data

            device_serial_id = validated.get("device_serial_id")
            value = validated.get("value")
            value_type = validated.get("value_type")
            ts = validated.get("ts")  # datetime obj
            device_metric_id = validated.get("device_metric_id")

            key = f"telemetry:{device_serial_id}:{device_metric_id}:{int(ts.timestamp())}"
            member = f"{value}"
            score = int(ts.timestamp())
            logger.debug("Adding to Redis: %s -> %s", key, member)
            redis_client.zadd(key, {member: score})
            redis_client.expire(key, TELEMETRY_KEY_TTL)

            telemetry = {
                "device_serial_id": device_serial_id,
                "device_metric_id": device_metric_id,
                "value": value,
                "value_type": value_type,
                "ts": ts.isoformat(),
            }

            self.rule_runner.delay(telemetry)

        except Exception:
            logger.exception("Failed to process telemetry payload: %s", item)
            rule_eval_errors_total.inc()


def main():
    """Starts the Kafka rule evaluation consumer"""
    logger.error("Kafka consumer starting on topics: %s", [CLEAN_TOPIC, EXPIRED_TOPIC])

    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[CLEAN_TOPIC, EXPIRED_TOPIC],
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
