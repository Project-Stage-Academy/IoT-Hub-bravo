import uuid
import logging
from decimal import Decimal
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.timezone import now

logger = logging.getLogger(__name__)


def _normalize_telemetry_value(value):
    """Return a JSON-serializable value for WebSocket payload."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Telemetry value not JSON-serializable: {type(value)}")


def _ts_to_iso(ts) -> str:
    """Normalize ts to ISO string (datetime or str accepted)."""
    if isinstance(ts, str):
        return ts
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    raise TypeError(f"Telemetry ts must be datetime or str, got {type(ts)}")


def publish_telemetry_event(
    *, device_serial_id: str, device_id: int, metric: str, metric_type: str, value, ts
) -> bool:
    """
    Publish a telemetry event to Channel layer groups (WebSocket).
    Returns True if sent successfully, False otherwise.
    Callers that require at-least-once delivery (e.g. Kafka handler) should raise on False.
    """
    value_safe = _normalize_telemetry_value(value)
    ts_str = _ts_to_iso(ts)
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
            "value": value_safe,
            "ts": ts_str,
        },
    }

    layer = get_channel_layer()
    if layer is None:
        logger.error("Channel layer is not configured")
        return False

    try:
        async_to_sync(layer.group_send)(
            "telemetry.global", {"type": "telemetry_update", "payload": payload}
        )
        async_to_sync(layer.group_send)(
            f"telemetry.device.{device_serial_id}",
            {"type": "telemetry_update", "payload": payload},
        )
        async_to_sync(layer.group_send)(
            f"telemetry.metric.{metric}",
            {"type": "telemetry_update", "payload": payload},
        )
        return True
    except Exception as e:
        logger.error("Error publishing telemetry event: %s", e)
        return False
