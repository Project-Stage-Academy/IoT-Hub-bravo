import os

import django

from .config import MqttConfig
from .mqtt_client import run_mqtt_client
from .message_handlers import CeleryMessageHandler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
django.setup()

from apps.devices.tasks import ingest_telemetry_payload  # noqa


def main() -> None:
    run_mqtt_client(
        config=MqttConfig(),
        handler=CeleryMessageHandler(ingest_telemetry_payload),
    )


if __name__ == "__main__":
    main()
