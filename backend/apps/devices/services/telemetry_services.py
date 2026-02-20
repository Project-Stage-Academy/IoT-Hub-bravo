import datetime
from dataclasses import dataclass, field
from typing import Any

from apps.devices.models import Device, Metric, DeviceMetric
from apps.devices.models.telemetry import Telemetry
from validator.telemetry_validator import TelemetryBatchValidator


@dataclass(slots=True)
class TelemetryIngestResult:
    created_count: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def telemetry_create(
    *,
    payload: dict,
) -> TelemetryIngestResult:
    """
    Service function to ingest telemetry. Creates multiple
    Telemetry objects for each metric-value pair provided.
    Metrics that do not exist, are not configured for
    given device, or contain values that do not match metric
    data type are skipped.
    """
    result = TelemetryIngestResult()

    validator = TelemetryBatchValidator(
        payload=payload
    )
    if not validator.is_valid():
        result.errors = validator.errors
        # logging logic
    
    # initialize Telemetry objects for every valid matric-value pair
    to_create: list[Telemetry] = []

    for row in validator.validated_rows:
        to_create.append(Telemetry(**row))

    if to_create:
        created = Telemetry.objects.bulk_create(
            to_create,
            batch_size=1000,
            ignore_conflicts=True,
        )
        result.created_count = len(created)

    return result
