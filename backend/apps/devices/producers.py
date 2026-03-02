from functools import lru_cache

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig

telemetry_raw_topic = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.raw')
telemetry_clean_topic = config('KAFKA_TOPIC_TELEMETRY_CLEAN', default='telemetry.clean')

# TODO: Shutdown

@lru_cache(maxsize=1)
def get_telemetry_raw_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=telemetry_raw_topic,
        poll_timeout=0.0,
    )

@lru_cache(maxsize=1)
def get_telemetry_clean_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=telemetry_clean_topic,
        poll_timeout=0.01
    )