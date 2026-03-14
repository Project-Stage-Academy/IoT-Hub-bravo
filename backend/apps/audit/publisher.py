from typing import Optional

from apps.audit.audit_record import AuditRecord
from apps.audit.producers import get_audit_producer
from producers.kafka_producer import KafkaProducer, ProduceResult


def publish_audit_event(
    *,
    event: AuditRecord,
    producer: Optional[KafkaProducer] = None,
) -> ProduceResult:
    """Publish audit event to Kafka."""

    if producer is None:
        producer = get_audit_producer()

    return producer.produce(
        payload=event.to_record(),
        key=event.event_type,
    )
