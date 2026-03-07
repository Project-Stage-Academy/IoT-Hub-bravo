import uuid
from django.utils import timezone
from django.core.management.base import BaseCommand
from decouple import config

from producers.kafka_producer import KafkaProducer
from producers.config import ProducerConfig


class Command(BaseCommand):
    help = 'Send a test rule event to Kafka for validating consumers.'

    def handle(self, *args, **options):
        topic = config('KAFKA_TOPIC_RULE_EVENTS', default='rules.events.triggered')

        self.stdout.write(f"Initializing Kafka producer for topic: {topic}...")

        producer = KafkaProducer(
            config=ProducerConfig(),
            topic=topic,
        )

        event_uuid = str(uuid.uuid4())

        payload = {
            "event_uuid": event_uuid,
            "rule_triggered_at": timezone.now().isoformat(),
            "rule_id": 4,
            "trigger_device_serial_id": "SN-A1-PRES-0003",
            "trigger_context": {
                "reason": "test_shot_from_console",
                "metric": "pressure",
                "value": 900.0,
                "threshold": 985.0,
            },
            "action": {
                "notification": {
                    "channel": "email",
                    "enabled": True,
                    "recipient": "0f8adc3e-6cab-4da0-972f-44b79f76b47a@emailhook.site",
                    "subject": "Critical Alert: Low Pressure Detected",
                    "message": "Atmospheric pressure has dropped below the safe threshold. Immediate check required.",
                },
                "webhook": {
                    "enabled": True,
                    "url": "https://webhook.site/0f8adc3e-6cab-4da0-972f-44b79f76b47a",
                    #"url": "https://httpstat.us/502", 
                }
            }
        }

        self.stdout.write(f"Sending event {event_uuid}...")

        result = producer.produce(payload=payload, key=str(payload["rule_id"]))
        producer.flush()

        self.stdout.write(self.style.SUCCESS(f"Event sent successfully. Result: {result}"))
        self.stdout.write("Check the consumer logs or the Django admin for details.")