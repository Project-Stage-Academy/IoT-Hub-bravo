import signal
import logging

from django.core.management.base import BaseCommand

from consumers.config import ConsumerConfig
from consumers.kafka_consumer import KafkaConsumer
from apps.devices.kafka_handlers.telemetry_clean_handler import TelemetryCleanHandler

logger = logging.getLogger(__name__)

TELEMETRY_CLEAN_TOPIC = "telemetry.clean"


class Command(BaseCommand):
    help = "Run Kafka consumer for telemetry.clean and push events to websockets."

    def handle(self, *args, **options):
        config = ConsumerConfig()
        config = config.__class__(
            group_id=config.group_id + "-telemetry-clean",
            **{name: getattr(config, name) for name in config.__dataclass_fields__ if name != "group_id"}
        ) if hasattr(ConsumerConfig, "__dataclass_fields__") else config

        consumer = KafkaConsumer(
            config=config,
            topics=[TELEMETRY_CLEAN_TOPIC],
            handler=TelemetryCleanHandler(),
            decode_json=True,
            consume_timeout=1.0,
        )

        signal.signal(signal.SIGTERM, consumer.stop)
        signal.signal(signal.SIGINT, consumer.stop)

        self.stdout.write("Starting telemetry.clean consumer...")
        consumer.start()