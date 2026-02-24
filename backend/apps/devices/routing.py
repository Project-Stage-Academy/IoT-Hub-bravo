from django.urls import re_path
from apps.devices.consumers.telemetry_consumer import TelemetryConsumer

websocket_urlpatterns = [
    re_path(r"ws/telemetry/stream/$", TelemetryConsumer.as_asgi()),
]
