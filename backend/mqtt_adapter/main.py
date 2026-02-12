import os

import django

from .config import MqttConfig
from .mqtt_client import run_mqtt_client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django.setup()

from apps.devices.tasks import ingest_telemetry_payload  # noqa


def main() -> None:
    run_mqtt_client(
        config=MqttConfig(),
        handle_payload=ingest_telemetry_payload.delay,
    )


if __name__ == '__main__':
    main()
