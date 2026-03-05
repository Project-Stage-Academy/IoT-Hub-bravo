import datetime
import logging
from typing import Any

from celery import shared_task
from django.db import OperationalError, InterfaceError
from producers.kafka_producer import ProduceResult

from .serializers.telemetry_serializers import TelemetryBatchCreateSerializer
from .services.telemetry_services import telemetry_create, telemetry_validate
from apps.devices.producers import (
    get_telemetry_clean_producer,
    get_telemetry_dlq_producer,
    get_telemetry_expired_producer
)

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
    payload = normalize_payload(payload)

    serializer = TelemetryBatchCreateSerializer(payload)

    if not serializer.is_valid() and not serializer.valid_items:
        logger.warning('Telemetry ingestion task rejected: errors=%s', len(serializer.errors))
        return

    total_created = 0
    total_errors = 0

    validation = telemetry_validate(payload=serializer.valid_items)
    r = telemetry_create(valid_data=validation.validated_rows)

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
    retry_kwargs={"max_retries": 10},
)
def validate_telemetry_payload(self, payload: dict | list) -> None:
    payload = normalize_payload(payload)

    serializer = TelemetryBatchCreateSerializer(payload)
    serializer.is_valid()

    if not serializer.valid_items:
        logger.warning("Telemetry validation rejected: no valid items.")
        return

    validation_result = telemetry_validate(payload=serializer.valid_items)

    logger.info(
        "Validation completed: received=%d, valid=%d, invalid=%d",
        len(payload),
        len(validation_result.validated_rows),
        len(validation_result.errors),
    )
    produce_validation_results(validation_result)
    return f"{validation_result.errors}, Expired: {validation_result.expired_rows}, Valid: {validation_result.validated_rows}"


@shared_task(
    bind=True,
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=10,
    retry_jitter=True,
    retry_kwargs={"max_retries": 10},
)
def write_telemetry_payload(self, payload: dict | list) -> None:
    payload = normalize_payload(payload)
    serializer = TelemetryBatchCreateSerializer(payload)
    serializer.validate_producer_batch(payload)

    if not serializer.valid_items:
        logger.warning("Write rejected: no valid items.")
        return serializer.item_errors

    result = telemetry_create(valid_data=serializer.valid_items)

    logger.info(
        "Write completed: received=%d, created=%d",
        len(payload),
        result.created_count,
    )


def normalize_payload(payload: dict | list) -> list | None:
    """
    Normalize payload to list.
    Returns None if invalid type.
    """
    if isinstance(payload, dict):
        return [payload]

    if isinstance(payload, list):
        return payload

    logger.error(f'payload must be of type dict or list, got {type(payload).__name__}')
    return

def produce_validation_results(validation_result) -> None:
    """
    Produce validation results into corresponding Kafka topics.
    """

    clean_producer = get_telemetry_clean_producer()
    dlq_producer = get_telemetry_dlq_producer()
    expired_producer = get_telemetry_expired_producer()
    
    # TODO: Async?
    produce_data(clean_producer, validation_result.validated_rows)
    produce_data(dlq_producer, validation_result.errors)
    produce_data(expired_producer, validation_result.expired_rows)


def produce_data(producer, data: list[dict[str, Any]]) -> None:
    """
    Produce batch of records to Kafka.
    """
    accepted = 0
    errors = {}

    for index, record in enumerate(data):
        ts = record.get("ts")

        if isinstance(ts, datetime.datetime):
            record["ts"] = ts.isoformat()

        result = producer.produce(
            payload=record,
            key=record.get("device_serial_id"),
        )

        if result == ProduceResult.ENQUEUED:
            accepted += 1
        else:
            errors[index] = result.value
    
    producer.flush()

    logger.info(
        "Produced %d/%d messages to topic %s",
        accepted,
        len(data),
        producer.topic,
    )

    if errors:
        logger.warning("Producer errors: %s", errors)

