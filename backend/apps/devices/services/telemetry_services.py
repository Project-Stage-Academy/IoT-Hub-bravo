import datetime
from dataclasses import dataclass, field
from typing import Any

from apps.devices.models import Device, Metric, DeviceMetric
from apps.devices.models.telemetry import Telemetry
from apps.devices.services.telemetry_stream_publisher import publish_telemetry_event


@dataclass(slots=True)
class TelemetryIngestResult:
    created_count: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def telemetry_create(
    *,
    device_serial_id: str,
    metrics: dict[str, Any],
    ts: datetime.datetime,
) -> TelemetryIngestResult:
    """
    Service function to ingest telemetry. Creates multiple
    Telemetry objects for each metric-value pair provided.
    Metrics that do not exist, are not configured for
    given device, or contain values that do not match metric
    data type are skipped.
    """
    result = TelemetryIngestResult()

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

    # create collected Telemetry objects
    created = Telemetry.objects.bulk_create(to_create, ignore_conflicts=True)
    result.created_count = len(created)

    # publish telemetry updates to websocket groups
    for evt in to_publish:
        publish_telemetry_event(**evt)

    return result


def _normalize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Utility function to normalize metric-value dictionary keys."""
    normalized = {}
    for name, value in metrics.items():
        name = name.strip()
        if name:
            normalized[name] = value
    return normalized


def _get_metrics_by_names(metrics_names: list[str]) -> dict[str, Metric]:
    """
    Utility function to retrieve Metric
    objects by provided metrics names.
    """
    return {m.metric_type: m for m in Metric.objects.filter(metric_type__in=metrics_names)}


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


def _value_matches_data_type(value: Any, data_type: str) -> bool:
    if data_type == "numeric":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if data_type == "bool":
        return isinstance(value, bool)
    if data_type == "str":
        return isinstance(value, str)
    return False
