import logging

from celery import shared_task
from django.db import OperationalError, InterfaceError

from .serializers.telemetry_serializers import TelemetryBatchCreateSerializer
from .services.telemetry_services import telemetry_create

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=10,
    retry_jitter=True,
    retry_kwargs={'max_retries': 10},
)
def ingest_telemetry_payload(self, payload: dict | list, **kwargs) -> None:
    if isinstance(payload, dict):
        payload = [payload]
    elif isinstance(payload, list):
        pass
    else:
        raise TypeError(f'payload must be of type dict or list, got {type(payload).__name__}')

    serializer = TelemetryBatchCreateSerializer(payload)

    if not serializer.is_valid() and not serializer.valid_items:
        logger.warning('Telemetry ingestion task rejected: errors=%s', len(serializer.errors))
        return

    total_created = 0
    total_errors = 0

    # for item in serializer.valid_items:
    # return serializer.valid_items
    r = telemetry_create(payload=serializer.valid_items)
    total_created += r.created_count
    total_errors += len(r.errors)

    return total_created

    invalid_items = serializer.item_errors
    invalid_count = len(invalid_items) if invalid_items else 0

    logger.info(
        'Telemetry task ingested batch: '
        'received=%s, valid=%s, invalid=%s, created=%s, item_errors=%s.',
        len(payload),
        len(serializer.valid_items),
        invalid_count,
        total_created,
        total_errors,
    )
