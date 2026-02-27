import json
from typing import Any, Callable, Optional

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.devices.serializers.telemetry_serializers import (
    TelemetryCreateSerializer,
    TelemetryBatchCreateSerializer,
)
from apps.devices.services.telemetry_services import (
    telemetry_create,
    telemetry_validate,
    TelemetryIngestResult,
)
from apps.devices.producers import get_telemetry_raw_producer
from producers.kafka_producer import KafkaProducer, ProduceResult

_RESERVED_RESPONSE_KEYS = {'status', 'created', 'errors'}

TelemetryIngestService = Callable[..., TelemetryIngestResult]

TELEMETRY_KEY_FIELD = getattr(settings, 'TELEMETRY_KEY_FIELD', 'device')


@csrf_exempt
@require_http_methods(['POST'])
def ingest_telemetry(request):
    payload, error_response = _parse_json_body(request.body)
    if error_response:
        return error_response

    if _should_ingest_sync(request):
        if isinstance(payload, dict):
            return _ingest_telemetry_single(payload)
        return _ingest_telemetry_batch(payload)

    return _produce_telemetry_records(payload=payload)


def _parse_json_body(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, JsonResponse({'errors': {'json': 'Invalid json.'}}, status=400)

    if not isinstance(payload, (dict, list)):
        return None, JsonResponse(
            {'errors': {'json': 'Payload must be a JSON object or a JSON array.'}},
            status=400,
        )
    return payload, None


def _should_ingest_sync(request, header_name=None) -> bool:
    if not settings.DEBUG:
        return False

    if header_name is None:
        header_name = getattr(settings, 'TELEMETRY_SYNC_HEADER', 'Ingest-Sync')

    if request.headers.get(header_name) == '1':
        return True
    return False


def _produce_telemetry_records(
    *,
    payload: dict | list,
    producer: Optional[KafkaProducer] = None,
):
    if not isinstance(payload, (dict, list)):
        return JsonResponse(
            {'errors': {'json': 'Payload must be a JSON object or a JSON array.'}},
            status=400,
        )

    if isinstance(payload, dict):
        payload = [payload]

    if len(payload) == 0:
        return JsonResponse(
            {'status': 'rejected', 'errors': {'payload': 'Payload array is empty.'}},
            status=422,
        )

    if producer is None:
        producer = get_telemetry_raw_producer()

    results = {
        'accepted': 0,
        'skipped': 0,
        'errors': {},
    }

    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            results['errors'][index] = 'Payload items must be JSON objects.'
            results['skipped'] += 1
            continue

        key = record.get(TELEMETRY_KEY_FIELD, None)

        result = producer.produce(payload=record, key=key)
        if result == ProduceResult.ENQUEUED:
            results['accepted'] += 1
        else:
            results['errors'][index] = result.value

    body = {'status': 'accepted', **results}
    status_code = 202

    # no valid records provided (all skipped / empty list)
    if results['accepted'] == 0 and results['skipped'] > 0:
        body['status'] = 'rejected'
        status_code = 422

    # no records accepted (kafka issues)
    elif results['accepted'] == 0 and results['errors']:
        body['status'] = 'unavailable'
        status_code = 503

    return JsonResponse(body, status=status_code)


def _ingest_telemetry_single(
    payload: dict,
    *,
    service: Optional[TelemetryIngestService] = None,
) -> JsonResponse:
    if service is None:
        service = telemetry_create

    serializer = TelemetryCreateSerializer(payload)
    if not serializer.is_valid():
        return JsonResponse({'errors': serializer.errors}, status=400)

    validation = telemetry_validate(serializer.validated_data)

    result = service(valid_data=validation.validated_rows, validation_errors=validation.errors)

    return _ingest_telemetry_json_response(
        created=result.created_count,
        errors=validation.errors,
    )


def _ingest_telemetry_batch(
    payload: list,
    *,
    service: Optional[TelemetryIngestService] = None,
) -> JsonResponse:
    if service is None:
        service = telemetry_create

    serializer = TelemetryBatchCreateSerializer(payload)
    if not serializer.is_valid() and not serializer.valid_items:
        return JsonResponse({'errors': serializer.errors}, status=400)

    total_created = 0
    items = []

    validation = telemetry_validate(serializer.valid_items)

    result = service(valid_data=validation.validated_rows, validation_errors=validation.errors)
    total_created += result.created_count
    items.append(
        {
            'created': result.created_count,
            'errors': validation.errors,
        }
    )

    return _ingest_telemetry_json_response(
        created=total_created,
        errors=serializer.item_errors,
        items=items,
    )


def _ingest_telemetry_json_response(
    *,
    created: int,
    errors: dict,
    **extra: Any,
) -> JsonResponse:
    duplicates = _RESERVED_RESPONSE_KEYS.intersection(extra.keys())
    if duplicates:
        raise ValueError(f'Extra contains reserved keys: {duplicates}')

    status_code = 201 if created > 0 else 422
    status_text = 'ok' if created > 0 else 'rejected'

    return JsonResponse(
        {
            'status': status_text,
            'created': created,
            **extra,
            'errors': errors,
        },
        status=status_code,
    )
