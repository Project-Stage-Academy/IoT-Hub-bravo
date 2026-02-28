import logging
from datetime import datetime
from typing import Any

from django.utils.dateparse import parse_datetime

from consumers.message_handlers import KafkaPayloadHandler
from apps.devices.services.telemetry_stream_publisher import publish_telemetry_event

logger = logging.getLogger(__name__)

class TelemetryCleanHandler(KafkaPayloadHandler):

    def handle(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            logger.error("Invalid payload type: %s", type(payload))
            return

        ts_raw = payload.get("ts")
        if ts_raw is None:
            logger.error("ts is required")
            return 

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

        publish_telemetry_event(
            device_serial_id=payload["device_serial_id"],
            device_id=payload["device_id"],
            metric=payload["metric"],
            metric_type=payload["metric_type"],
            value=payload["value"],
            ts=ts,
        )