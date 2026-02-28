import json
from typing import Any, Callable, Optional, Protocol

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
    TelemetryIngestResult,
)
from apps.devices.tasks import ingest_telemetry_payload


class CeleryDelayTask(Protocol):
    def delay(self, payload) -> Any: ...


_RESERVED_RESPONSE_KEYS = {"status", "created", "errors"}

TelemetryIngestService = Callable[..., TelemetryIngestResult]


@csrf_exempt
@require_http_methods(["POST"])
def ingest_telemetry(request):
    payload, error_response = _parse_json_body(request.body)
    if error_response:
        return error_response

    if _should_ingest_async(request, payload):
        return _enqueue_async_ingest(payload)

    if isinstance(payload, dict):
        return _ingest_telemetry_single(payload)

    return _ingest_telemetry_batch(payload)


def _parse_json_body(body: bytes) -> tuple:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, JsonResponse({"errors": {"json": "Invalid json."}}, status=400)

    if not isinstance(payload, (dict, list)):
        return None, JsonResponse(
            {"errors": {"json": "Payload must be a JSON object or a JSON array."}},
            status=400,
        )
    return payload, None


def _should_ingest_async(request, payload, *, header_name=None, threshold=None) -> bool:
    if header_name is None:
        header_name = getattr(settings, "TELEMETRY_ASYNC_HEADER", "Ingest-Async")
    if threshold is None:
        threshold = getattr(settings, "TELEMETRY_ASYNC_BATCH_THRESHOLD", 50)

    if request.headers.get(header_name) == "1":
        return True
    return isinstance(payload, list) and len(payload) > threshold


def _enqueue_async_ingest(
    payload: dict | list,
    *,
    task: Optional[CeleryDelayTask] = None,
) -> JsonResponse:
    if task is None:
        task = ingest_telemetry_payload

    task.delay(payload)
    return JsonResponse({"status": "accepted"}, status=202)


def _ingest_telemetry_single(
    payload: dict,
    *,
    service: Optional[TelemetryIngestService] = None,
) -> JsonResponse:
    if service is None:
        service = telemetry_create

    serializer = TelemetryCreateSerializer(payload)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)

    result = service(**serializer.validated_data)

    return _ingest_telemetry_json_response(
        created=result.created_count,
        errors=result.errors,
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
        return JsonResponse({"errors": serializer.errors}, status=400)

    total_created = 0
    items = []

    for item in serializer.valid_items:
        result = service(**item)
        total_created += result.created_count
        items.append(
            {
                "created": result.created_count,
                "errors": result.errors,
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
        raise ValueError(f"Extra contains reserved keys: {duplicates}")

    status_code = 201 if created > 0 else 422
    status_text = "ok" if created > 0 else "rejected"

    return JsonResponse(
        {
            "status": status_text,
            "created": created,
            **extra,
            "errors": errors,
        },
        status=status_code,
    )
