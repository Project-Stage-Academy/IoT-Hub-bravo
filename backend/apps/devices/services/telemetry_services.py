import logging
from dataclasses import dataclass, field
from typing import Literal

from apps.devices.models.telemetry import Telemetry
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
    validation_errors: list[dict] = field(default_factory=list)
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

    logger.info(
        "Starting telemetry ingestion. Attempting to create %d rows.",
        result.attempted_count,
    )

    if not valid_data:
        logger.info("No valid telemetry rows to create.")

        result.status = "failed" if result.validation_errors else "success"
        return result

    to_create = [Telemetry(**row) for row in valid_data]

    created_objects = Telemetry.objects.bulk_create(
        to_create,
        batch_size=1000,
        ignore_conflicts=True,
    )

    result.created_count = len(created_objects)

    logger.info(
        "Telemetry ingestion finished. Attempted: %d, Created: %d",
        result.attempted_count,
        result.created_count,
    )

    if result.validation_errors and result.created_count == 0:
        result.status = "failed"

    elif result.validation_errors:
        result.status = "partial_success"

    else:
        result.status = "success"

    return result


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

    return TelemetryValidationResult(
        validated_rows=validator.validated_rows, errors=validator.errors
    )
