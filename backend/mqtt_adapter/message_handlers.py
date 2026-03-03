from typing import Any, Protocol, Optional
from dataclasses import dataclass
import logging

from producers.kafka_producer import KafkaProducer

logger = logging.getLogger(__name__)
JsonPayload = dict[str, Any] | list[Any]


@dataclass(frozen=True, slots=True)
class MQTTJsonMessage:
    topic: str
    qos: int
    retain: bool
    payload: JsonPayload


class MessageHandler(Protocol):
    """
    Handles decoded MQTT JSON messages.

    This handler is invoked from the Paho MQTT client loop thread.
    Implementations must be fast / non-blocking.
    """

    def handle(self, message: MQTTJsonMessage) -> None: ...


class CeleryMessageHandler:
    def __init__(self, celery_task):
        self._task = celery_task

    def handle(self, message: MQTTJsonMessage) -> None:
        self._task.delay(
            message.payload,
            topic=message.topic,
            qos=message.qos,
            retain=message.retain,
        )


class KafkaProducerMessageHandler:
    def __init__(self, producer: KafkaProducer, key_field: Optional[str] = None):
        self._producer = producer
        self._key_field = key_field

    def _extract_key(self, payload: dict) -> Optional[str]:
        if self._key_field:
            return payload.get(self._key_field, None)
        return None

    def handle(self, message: MQTTJsonMessage) -> None:
        if isinstance(message.payload, dict):
            key = self._extract_key(message.payload)
            self._producer.produce(payload=message.payload, key=key)
            return

        skipped = 0
        for record in message.payload:
            if not isinstance(record, dict):
                skipped += 1
                continue

            key = self._extract_key(record)
            self._producer.produce(payload=record, key=key)

        if skipped:
            logger.warning(
                'MQTT batch contained non-object items; skipped=%s, topic=%s, qos=%s, retain=%s.',
                skipped,
                message.topic,
                message.qos,
                message.retain,
            )
