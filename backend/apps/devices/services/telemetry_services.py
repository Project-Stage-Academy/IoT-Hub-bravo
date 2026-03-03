import logging
from dataclasses import dataclass, field
from typing import Literal

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
    """
    logger.info("Starting telemetry ingestion for %d items", len(valid_data))

    result = TelemetryIngestResult()
    result.errors = validation_errors or []
    result.attempted_count = len(valid_data)

    # validate device
    try:
        device = Device.objects.get(serial_id=device_serial_id)
    except Device.DoesNotExist:
        result.errors["device"] = "Device not found."
        return result

    if not device.is_active:
        result.errors["device"] = "Device is not active."
        return result

    # collect Metric and DeviceMetric objects for passed metrics
    normalized_metrics = _normalize_metrics(metrics)
    if not normalized_metrics:
        result.errors["metrics"] = "No valid metric names."
        return result

    metrics_names = list(normalized_metrics.keys())
    metrics_by_name = _get_metrics_by_names(metrics_names)
    device_metrics = _get_device_metrics_by_names(device, metrics_names)

    # initialize Telemetry objects for every valid metric-value pair
    to_create: list[Telemetry] = []
    to_publish: list[dict[str, Any]] = []

    for name, value in normalized_metrics.items():
        metric = metrics_by_name.get(name)
        if metric is None:
            result.errors[name] = "metric does not exist."
            continue

        dm = device_metrics.get(name)
        if dm is None:
            result.errors[name] = "metric not configured for device."
            continue

        if not _value_matches_data_type(value, metric.data_type):
            result.errors[name] = f"Type mismatch (expected {metric.data_type})"
            continue

        to_create.append(
            Telemetry(
                device_metric=dm,
                ts=ts,
                value_jsonb={
                    "t": metric.data_type,
                    "v": value,
                },
            )
        )

        to_publish.append(
            {
                "device_serial_id": device.serial_id,
                "device_id": device.id,
                "metric": name,
                "metric_type": metric.data_type,
                "value": value,
                "ts": ts,
            }
        )

    if not to_create:
        return result

    logger.info(
        "Starting telemetry ingestion. Attempting to create %d rows.",
        result.attempted_count,
    )

    if not valid_data:
        logger.info("No valid telemetry rows to create.")

        result.status = "failed" if result.errors else "success"
        return result

    to_create = [Telemetry(**row) for row in valid_data]

    created_objects = Telemetry.objects.bulk_create(
        to_create,
        batch_size=1000,
        ignore_conflicts=True,
    )
    result.created_count = len(created_objects)

    # publish telemetry updates to websocket groups
    for evt in to_publish:
        publish_telemetry_event(**evt)

    return result

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
