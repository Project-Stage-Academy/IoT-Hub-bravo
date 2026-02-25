import json
import logging
from typing import Any, Optional
from enum import Enum

from confluent_kafka import Producer, Message, KafkaException, KafkaError

from producers.config import ProducerConfig

logger = logging.getLogger(__name__)


class ProduceResult(Enum):
    ENQUEUED = 'enqueued'
    SERIALIZATION_FAILED = 'serialization_failed'
    BUFFER_FULL = 'buffer_full'
    PRODUCER_ERROR = 'producer_error'


class KafkaProducer:
    def __init__(
        self,
        *,
        config: ProducerConfig,
        topic: str,
        poll_timeout: float = 0.0,
    ):
        self._producer = Producer(config.to_kafka_dict())
        self._topic = topic
        self._poll_timeout = poll_timeout
        self._dropped_messages = 0

    def produce(self, payload: Any, key: Any = None) -> ProduceResult:
        """
        Produce a message to the configured Kafka topic asynchronously.

        Serializes payload to UTF-8 JSON bytes, encodes key to bytes if provided
        and submits the message to the Kafka producer for asynchronous delivery
        to the configured topic.

        Returns:
            ENQUEUED - the message was accepted by the producer and queued for delivery;
            SERIALIZATION_FAILED - value serialization failed;
            BUFFER_FULL - producer queue is full;
            PRODUCER_ERROR - producer error occurred.
        """
        value = self._encode_payload(payload)
        if value is None:
            return ProduceResult.SERIALIZATION_FAILED

        key_bytes = self._encode_key(key)

        try:
            self._producer.produce(
                topic=self._topic,
                value=value,
                key=key_bytes,
                on_delivery=self._delivery_report,
            )
            result = ProduceResult.ENQUEUED
        except BufferError:
            self._dropped_messages += 1
            self._producer.poll(0)
            logger.warning('Kafka producer local buffer full. Dropped: %s', self._dropped_messages)
            result = ProduceResult.BUFFER_FULL
        except KafkaException:
            logger.exception('Kafka produce failed.')
            result = ProduceResult.PRODUCER_ERROR
        finally:
            self._producer.poll(self._poll_timeout)

        return result

    def flush(self, timeout: float = 2.0) -> None:
        """Graceful shutdown: flush pending messages."""
        logger.info('Shutting down the producer...')
        self._producer.flush(timeout)

    @staticmethod
    def _encode_payload(payload: Any) -> Optional[bytes]:
        try:
            return json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        except (TypeError, ValueError):
            logger.exception('Failed to JSON-encode payload.')
            return None

    @staticmethod
    def _encode_key(key: Optional[Any]) -> Optional[bytes]:
        if key is None or isinstance(key, bytes):
            return key
        if isinstance(key, str):
            s = key.strip()
            return s.encode('utf-8') if s else None
        return str(key).encode('utf-8')

    @staticmethod
    def _delivery_report(error: KafkaError, message: Message) -> None:
        extra = {
            'topic': message.topic(),
            'partition': message.partition(),
            'error': error,
        }
        if error is not None:
            logger.warning('Kafka delivery failed.', extra=extra)
