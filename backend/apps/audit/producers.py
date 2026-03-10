from functools import lru_cache

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig

AUDIT_TOPIC = config('KAFKA_TOPIC_AUDIT', default='audit.records')


@lru_cache(maxsize=1)
def get_audit_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=AUDIT_TOPIC,
        poll_timeout=0.0,
    )
