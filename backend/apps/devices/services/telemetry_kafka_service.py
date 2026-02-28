import logging
from typing import Any

from producers.config import ProducerConfig
from producers.kafka_producer import KafkaProducer

logger = logging.getLogger(__name__)

_telemetry_producer: KafkaProducer | None = None

TELEMETRY_TOPIC = "telemetry.clean"

def get_telemetry_producer() -> KafkaProducer:
    global _telemetry_producer
    if _telemetry_producer is None:
        try:
            _telemetry_producer = KafkaProducer(
                config=ProducerConfig(),
                topic=TELEMETRY_TOPIC,
            )
        except Exception as e:
            logger.error(f"Error creating telemetry producer: {e}")
    return _telemetry_producer


def produce_telemetry_clean(payload: dict) -> bool:
    producer = get_telemetry_producer()
    if producer is None:
        logger.error("Telemetry producer is not initialized")
        return False
    return producer.produce(payload)