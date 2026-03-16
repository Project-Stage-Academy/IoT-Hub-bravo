import logging
from datetime import datetime
from typing import Any

from django.utils.dateparse import parse_datetime

from consumers.message_handlers import KafkaPayloadHandler
from apps.devices.services.telemetry_stream_publisher import publish_telemetry_event

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "device_serial_id",
    "device_id",
    "metric",
    "metric_type",
    "value",
    "ts",
]


class WebSocketTelemetryCleanHandler(KafkaPayloadHandler):

    def handle(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            logger.error("Invalid payload type: %s", type(payload))
            return

        missing = [f for f in REQUIRED_FIELDS if f not in payload]
        if missing:
            logger.error("telemetry.clean missing required fields: %s", ", ".join(missing))
            return

        # Type and format validation for critical fields
        device_serial_id = payload.get("device_serial_id")
        if not isinstance(device_serial_id, str) or not (device_serial_id or "").strip():
            logger.error("telemetry.clean 'device_serial_id' must be a non-empty string, got %s", type(device_serial_id))
            return
        device_id = payload.get("device_id")
        if not isinstance(device_id, int):
            logger.error("telemetry.clean 'device_id' must be int, got %s", type(device_id))
            return
        metric = payload.get("metric")
        if not isinstance(metric, str) or not (metric or "").strip():
            logger.error("telemetry.clean 'metric' must be a non-empty string, got %s", type(metric))
            return
        metric_type = payload.get("metric_type")
        if not isinstance(metric_type, str) or not (metric_type or "").strip():
            logger.error("telemetry.clean 'metric_type' must be a non-empty string, got %s", type(metric_type))
            return

        ts_raw = payload["ts"]
        if isinstance(ts_raw, str):
            ts = parse_datetime(ts_raw)
            if ts is None:
                logger.warning("telemetry.clean invalid 'ts': %s", ts_raw)
                return
        elif isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            logger.warning("telemetry.clean 'ts' type not supported: %s", type(ts_raw))
            return

        value = payload["value"]

        try:
            if not publish_telemetry_event(
                device_serial_id=device_serial_id,
                device_id=device_id,
                metric=metric,
                metric_type=metric_type,
                value=value,
                ts=ts,
            ):
                logger.error("telemetry.clean: publish_telemetry_event returned False")
                raise RuntimeError(
                    "Failed to publish telemetry to channel layer; offset will not be committed."
                )
        except (TypeError, ValueError) as e:
            logger.warning("telemetry.clean skipped message due to invalid data: %s", e)
            return
