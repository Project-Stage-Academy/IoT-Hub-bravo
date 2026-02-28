from django.urls import path

from apps.devices.views import ingest_telemetry

urlpatterns = [
    path("", ingest_telemetry, name="ingest-telemetry"),
]
