import uuid
import logging
from django.utils import timezone

from apps.rules.models.rule import Rule
from apps.rules.utils.rule_engine_utils import TelemetryEvent
from apps.common.metrics import events_created_total

from decouple import config
from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig

logger = logging.getLogger(__name__)

KAFKA_TOPIC = config('KAFKA_TOPIC_RULE_EVENTS', default='rules.events.triggered')
rule_event_producer = KafkaProducer(config=ProducerConfig(), topic=KAFKA_TOPIC)


class Action:
    """
    Handles dispatching side-effects for a triggered rule by producing an event to Kafka.
    """

    @staticmethod
    def dispatch_action(rule: Rule, telemetry: TelemetryEvent) -> str:
        """
        Produce Event to Kafka instead of creating it in the DB directly.
        Returns the generated event_uuid.
        """
        severity = 'info'
        if rule.action and isinstance(rule.action, dict):
            severity = rule.action.get('severity', 'info')

        events_created_total.labels(severity=severity).inc()

        event_uuid = str(uuid.uuid4())

        payload = {
            "event_uuid": event_uuid,
            "rule_triggered_at": timezone.now().isoformat(),
            "rule_id": rule.id,
            "trigger_device_serial_id": telemetry.device_serial_id,
            "trigger_context": {
                "metric_type": telemetry.metric_type,
                "value": float(telemetry.value) if telemetry.value is not None else None,
                "telemetry_timestamp": telemetry.timestamp.isoformat(),
            },
            "action": rule.action if isinstance(rule.action, dict) else {},
        }

        logger.info(
            "Producing Rule Event to Kafka",
            extra={
                "context": {
                    "event_uuid": event_uuid,
                    "rule_id": rule.id,
                    "trigger_device_serial_id": telemetry.device_serial_id,
                }
            },
        )

        try:
            rule_event_producer.produce(payload=payload, key=str(rule.id))

            rule_event_producer.flush()

        except Exception:
            logger.exception('Failed to publish event to Kafka')
