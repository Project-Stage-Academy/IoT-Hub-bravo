import datetime
from dataclasses import dataclass, field
from typing import Any

from apps.devices.models import Device, Metric, DeviceMetric
from apps.devices.models.telemetry import Telemetry
from validator.telemetry_validator import TelemetryValidator


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

    validator = TelemetryValidator(
        device_serial_id=device_serial_id,
        metrics=metrics,
        ts=ts,
    )
    print("Validator created with:", device_serial_id, metrics, ts)
    if not validator.is_valid():
        result.errors = validator.errors
        # logging logic
    
    # initialize Telemetry objects for every valid matric-value pair
    to_create: list[Telemetry] = []
    for name, info in validator.validated_metrics.items():
        dm = info["device_metric"]
        value = info["value"]
        data_type = info["metric"].data_type

        to_create.append(
            Telemetry(
                device_metric=dm,
                ts=ts,
                value_jsonb={
                    't': data_type,
                    'v': value,
                },
            )
        )
    
    if to_create:
        created = Telemetry.objects.bulk_create(to_create, ignore_conflicts=True)
        result.created_count = len(created)

    return result
