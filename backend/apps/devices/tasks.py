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
def ingest_telemetry_payload(self, payload: dict | list) -> None:
    if isinstance(payload, dict):
        payload = [payload]
    elif not isinstance(payload, list):
        logger.warning('Telemetry ingestion task rejected: payload must be of type dict or list')
        return

    serializer = TelemetryBatchCreateSerializer(payload)

    if not serializer.is_valid() and not serializer.valid_items:
        logger.warning(f'Telemetry ingestion task rejected: errors={len(serializer.errors)}')
        return

    total_created = 0
    total_errors = 0

    for item in serializer.valid_items:
        r = telemetry_create(**item)
        total_created += r.created_count
        total_errors += len(r.errors)

    invalid_items = serializer.item_errors
    invalid_count = len(invalid_items) if invalid_items else 0

    logger.info(
        f'Telemetry task ingested batch: '
        f'received={len(payload)}, '
        f'valid={len(serializer.valid_items)}, '
        f'invalid={invalid_count}, '
        f'created={total_created}, '
        f'item_errors={total_errors}.'
    )
