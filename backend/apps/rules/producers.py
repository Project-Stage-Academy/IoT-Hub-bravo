from functools import lru_cache

from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig


rule_events_topic = config('KAFKA_TOPIC_RULE_EVENTS', default='events.rule_triggered')


@lru_cache(maxsize=1)
def get_rule_event_producer() -> KafkaProducer:
    return KafkaProducer(
        config=ProducerConfig(),
        topic=rule_events_topic,
        poll_timeout=0.0,
    )
