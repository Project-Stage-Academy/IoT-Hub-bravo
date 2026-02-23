import logging
from dataclasses import dataclass, field

from apps.devices.models.telemetry import Telemetry
from validator.telemetry_validator import TelemetryBatchValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TelemetryIngestResult:
    created_count: int = 0
    errors: dict[str, str] = field(default_factory=dict)


def telemetry_create(
    *,
    payload: list[dict],
) -> TelemetryIngestResult:
    """
    Service function to ingest telemetry. Creates multiple
    Telemetry objects for each metric-value pair provided.
    Metrics that do not exist, are not configured for
    given device, or contain values that do not match metric
    data type are skipped.
    """
    logger.info("Starting telemetry ingestion for %d items", len(payload))

    result = TelemetryIngestResult()
    validator = TelemetryBatchValidator(payload=payload)
    if not validator.is_valid():
        result.errors = validator.errors
        logger.warning(
            "Telemetry validation failed for %d items. Errors: %s", len(payload), validator.errors
        )
        # If no valid rows, we can return early
        if not validator.validated_rows:
            logger.info("No valid telemetry rows to create. Exiting.")
            return result

    logger.info(
        "Telemetry validation succeeded. %d valid rows ready for creation.",
        len(validator.validated_rows),
    )

    # initialize Telemetry objects for every valid matric-value pair
    to_create: list[Telemetry] = []
    for row in validator.validated_rows:
        to_create.append(Telemetry(**row))

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
