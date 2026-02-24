import logging
from dataclasses import dataclass, field

from apps.devices.models.telemetry import Telemetry
from validator.telemetry_validator import TelemetryBatchValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TelemetryIngestResult:
    created_count: int = 0
    errors: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class TelemetryValidationResult:
    validated_rows: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


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

    to_create: list[Telemetry] = [Telemetry(**row) for row in valid_data]

    logger.debug("Prepared %d Telemetry objects to create", len(to_create))

    if to_create:
        created = Telemetry.objects.bulk_create(
            to_create,
            batch_size=1000,
            ignore_conflicts=True,
        )
        result.created_count = len(created)
        logger.info("Successfully created %d Telemetry records in DB", result.created_count)
    else:
        logger.info("No Telemetry records to create after validation")

    logger.info("Telemetry ingestion completed")

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
