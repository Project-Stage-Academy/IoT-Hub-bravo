import uuid
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.timezone import now

logger = logging.getLogger(__name__)


def publish_telemetry_event(
    *, device_serial_id: str, device_id: int, metric: str, metric_type: str, value, ts
):
    payload = {
        "event_id": str(uuid.uuid4()),
        "type": "telemetry.update",
        "schema_version": 1,
        "sent_at": now().isoformat(),
        "data": {
            "device_serial_id": device_serial_id,
            "device_id": device_id,
            "metric": metric,
            "metric_type": metric_type,
            "value": value,
            "ts": ts.isoformat(),
        },
    }

    layer = get_channel_layer()

    if layer is None:
        logger.error("Channel layer is not configured")
        return

    try:
        async_to_sync(layer.group_send)(
            "telemetry.global", {"type": "telemetry_update", "payload": payload}
        )
        async_to_sync(layer.group_send)(
            f"telemetry.device.{device_serial_id}",
            {"type": "telemetry_update", "payload": payload},
        )
        async_to_sync(layer.group_send)(
            f"telemetry.metric.{metric}", {"type": "telemetry_update", "payload": payload}
        )
    except Exception as e:
        logger.error(f"Error publishing telemetry event: {e}")
