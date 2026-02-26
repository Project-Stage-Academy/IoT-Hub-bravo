from functools import lru_cache

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig

telemetry_raw_topic = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')


@lru_cache(maxsize=1)
def get_telemetry_raw_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=telemetry_raw_topic,
        poll_timeout=0.0,
    )
