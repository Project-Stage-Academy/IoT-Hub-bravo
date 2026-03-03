import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from apps.devices.models import Device, DeviceMetric
from apps.devices.models.telemetry import Telemetry
from apps.devices.services.telemetry_stream_publisher import publish_telemetry_event
from validator.telemetry_validator import TelemetryBatchValidator

logger = logging.getLogger(__name__)

IngestStatus = Literal["success", "partial_success", "failed"]


@dataclass(slots=True)
class TelemetryValidationResult:
    validated_rows: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class TelemetryIngestResult:
    attempted_count: int = 0  # how many rows we tried to create
    created_count: int = 0  # how many were actually inserted
    errors: list[dict] = field(default_factory=list)
    status: IngestStatus = "success"


def telemetry_create(
    *, valid_data: list[dict], validation_errors: list[dict] | None = None
) -> TelemetryIngestResult:
    """
    Service function to ingest telemetry. Creates multiple
    Telemetry objects for each metric-value pair provided.
    valid_data is expected to be validator's validated_rows:
    list of dicts with device_metric_id, ts, value_jsonb.
    """
    logger.info("Starting telemetry ingestion for %d items", len(valid_data))

    result = TelemetryIngestResult()
    result.errors = validation_errors or []
    result.attempted_count = len(valid_data)

    if not valid_data:
        logger.info("No valid telemetry rows to create.")
        result.status = "failed" if result.errors else "success"
        return result

    # Load DeviceMetrics for publish payloads
    dm_ids = [row["device_metric_id"] for row in valid_data]
    device_metrics_map = {
        dm.id: dm
        for dm in DeviceMetric.objects.filter(id__in=dm_ids).select_related("device", "metric")
    }

    to_create = [
        Telemetry(
            device_metric_id=row["device_metric_id"],
            ts=row["ts"],
            value_jsonb=row["value_jsonb"],
        )
        for row in valid_data
    ]

    logger.info(
        "Attempting to create %d telemetry rows.",
        result.attempted_count,
    )

    created_objects = Telemetry.objects.bulk_create(
        to_create,
        batch_size=1000,
        ignore_conflicts=True,
    )
    result.created_count = len(created_objects)

    # Publish telemetry updates to websocket groups
    for row in valid_data:
        dm = device_metrics_map.get(row["device_metric_id"])
        if dm is not None:
            publish_telemetry_event(
                device_serial_id=dm.device.serial_id,
                device_id=dm.device.id,
                metric=dm.metric.metric_type,
                metric_type=dm.metric.data_type,
                value=row["value_jsonb"].get("v"),
                ts=row["ts"],
            )

    if result.errors and result.created_count == 0:
        result.status = "failed"
    elif result.errors:
        result.status = "partial_success"
    else:
        result.status = "success"

    return result


def _get_device_metrics_by_names(
    device: Device,
    metrics_names: list[str],
) -> dict[str, DeviceMetric]:
    """
    Utility function to retrieve DeviceMetric
    objects by provided metrics names.
    """
    qs = DeviceMetric.objects.select_related("metric").filter(
        device=device, metric__metric_type__in=metrics_names
    )
    return {dm.metric.metric_type: dm for dm in qs}


def telemetry_validate(payload: dict | list[dict]) -> TelemetryValidationResult:
    if isinstance(payload, dict):
        payload_list = [payload]
    else:
        payload_list = payload

    validator = TelemetryBatchValidator(payload=payload_list)
    validator.is_valid()

    if validator.errors:
        logger.warning(
            "Telemetry validation completed with errors for %d items. Errors: %s",
            len(payload),
            validator.errors,
        )

    logger.info(
        "Telemetry validation completed. %d valid rows ready for creation.",
        len(validator.validated_rows),
    )


def _value_matches_data_type(value: Any, data_type: str) -> bool:
    if data_type == "numeric":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if data_type == "bool":
        return isinstance(value, bool)
    if data_type == "str":
        return isinstance(value, str)
    return False
