import datetime
import logging
from typing import Any

from celery import shared_task
from django.db import OperationalError, InterfaceError
from producers.kafka_producer import ProduceResult

from .serializers.telemetry_serializers import TelemetryBatchCreateSerializer
from .services.telemetry_services import telemetry_create, telemetry_validate
from apps.devices.producers import get_telemetry_clean_producer


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

    if not serializer.validate_producer_batch(payload) and not serializer.valid_items:
        logger.warning('Telemetry ingestion task rejected: errors=%s', len(serializer.errors))
        return f"Valid: {serializer.valid_items}, errors: {serializer.errors}"

    total_created = 0
    total_errors = 0

    # for item in serializer.valid_items:
    # return serializer.valid_items
    r = telemetry_create(valid_data=serializer.valid_items)
    total_created += r.created_count
    total_errors += len(r.errors)

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

@shared_task(
    bind=True,
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=10,
    retry_jitter=True,
    retry_kwargs={'max_retries': 10},
)
def validate_telemetry_payload(self,payload):
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

    total_errors = 0
    # for item in serializer.valid_items:
    # return serializer.valid_items
    r = telemetry_validate(payload=serializer.valid_items)
    validated_items = r.validated_rows
    total_errors += len(r.errors)
    # return r.errors
    invalid_items = serializer.item_errors
    invalid_count = len(invalid_items) if invalid_items else 0

    logger.info(
        'Telemetry task ingested batch: '
        'received=%s, valid=%s, invalid=%s, created=%s, item_errors=%s.',
        len(payload),
        len(serializer.valid_items),
        invalid_count,
        validated_items,
        total_errors,
    )
    # return validated_items
    if not validated_items:
        logger.info("No validated items to produce.")
        return

    # TODO: move producer to separate function
    producer = get_telemetry_clean_producer()
    results = {'accepted': 0, 'skipped': 0, 'errors': {}}
    for index, record in enumerate(validated_items):
        if isinstance(record.get('ts'), datetime.datetime):
            record['ts'] = record['ts'].isoformat()

        key = record.get('device_metric_id')
        result = producer.produce(payload=record, key=key)

        if result == ProduceResult.ENQUEUED:
            results['accepted'] += 1
        else:
            results['errors'][index] = result.value
    producer.flush()
    logger.info("Produced %d items to clean topic.", results['accepted'])
