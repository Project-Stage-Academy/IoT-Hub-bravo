from functools import lru_cache

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig

external_events_topic = config('KAFKA_TOPIC_EXTERNAL_EVENTS', default='rules.events.external')

# TODO: Shutdown


@lru_cache(maxsize=1)
def get_external_events_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=external_events_topic,
        poll_timeout=0.0,
    )
