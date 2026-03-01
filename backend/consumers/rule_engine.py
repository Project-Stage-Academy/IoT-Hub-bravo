# rule eval for telemetry stream (????)

import logging
import os
import signal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
import django
from decouple import config

django.setup()

from consumers.kafka_consumer import KafkaConsumer
from consumers.config import ConsumerConfig
from consumers.message_handlers import RuleEvalHandler


# change to telemetry.clean
topic = config('KAFKA_TOPIC_TELEMETRY_RAW', default='telemetry.clean')


def main():
    """
    Consumer for SHITS and TELEMTRY
    """
    consumer = KafkaConsumer(
        config=ConsumerConfig(),
        topics=[topic],
        handler=RuleEvalHandler(),
        consume_timeout=1.0,
        decode_json=True,
        consume_batch=True,
        batch_max_size=100,
    )

    signal.signal(signal.SIGTERM, consumer.stop)
    signal.signal(signal.SIGINT, consumer.stop)

    consumer.start()


if __name__ == '__main__':
    main()

