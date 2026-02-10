import json
from typing import Any, Callable, Optional, Protocol

from django.conf import settings
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.views import View

from apps.devices.models import Device
from apps.users.decorators import jwt_required, role_required
from .serializers.device_serializers.base_device_serializer import DeviceOutputSerializer
from .serializers.device_serializers.create_device_serializer import DeviceCreateV1Serializer
from .serializers.device_serializers.update_device_serializer import DeviceUpdateV1Serializer
from .serializers.telemetry_serializers import (
    TelemetryCreateSerializer,
    TelemetryBatchCreateSerializer,
)
from .services.device_service import DeviceService
from .services.telemetry_services import (
    telemetry_create,
    TelemetryIngestResult,
)
from .tasks import ingest_telemetry_payload


class CeleryDelayTask(Protocol):
    def delay(self, payload) -> Any: ...


_RESERVED_RESPONSE_KEYS = {'status', 'created', 'errors'}

TelemetryIngestService = Callable[..., TelemetryIngestResult]


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(jwt_required, name="dispatch")
@method_decorator(role_required({"GET": ["client", "admin"], "POST": ["admin"]}), name="dispatch")
class DeviceView(View):

    def parse_json_request(self, body: bytes):
        try:
            return json.loads(body), None
        except json.JSONDecodeError:
            return None, JsonResponse({"error": "Invalid JSON"}, status=400)

    def get(self, request):
        try:
            limit = int(request.GET.get("limit", 5))
            offset = int(request.GET.get("offset", 0))
        except ValueError:
            return JsonResponse({"error": "limit and offset must be integers"}, status=400)

        if limit <= 0:
            return JsonResponse({"error": "Limit must be greater than 0"}, status=400)
        if offset < 0:
            return JsonResponse({"error": "Offset must be positive integer"}, status=400)
        devices_qs = Device.objects.select_related("user").all().order_by("id")
        total = devices_qs.count()
        devices = devices_qs[offset : offset + limit]
        data = [DeviceOutputSerializer().to_representation(instance=d) for d in devices]
        return JsonResponse({"total": total, "limit": limit, "offset": offset, "items": data})

    def post(self, request):
        data, error_response = self.parse_json_request(request.body)
        if error_response:
            return error_response

        schema_version = data.get("schema_version")
        if not schema_version:
            return JsonResponse({"error": "schema_version is required"}, status=400)

        SERIALIZERS = {
            "v1": DeviceCreateV1Serializer,
        }

        SerializerClass = SERIALIZERS.get(schema_version)
        if not SerializerClass:
            return JsonResponse({"error": "Wrong schema_version!"}, status=400)

        serializer = SerializerClass(data=data.get("device"))
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)

        canonical_data = serializer.to_canonical()
        device = DeviceService.create_device(**canonical_data)
        return JsonResponse(
            DeviceOutputSerializer().to_representation(instance=device), status=201
        )

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["GET", "POST"])


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(
    role_required(
        {"GET": ["client", "admin"], "PUT": ["admin"], "PATCH": ["admin"], "DELETE": ["admin"]}
    ),
    name='dispatch',
)
class DeviceDetailView(View):
    def parse_json_request(self, body: bytes):
        try:
            return json.loads(body), None
        except json.JSONDecodeError:
            return None, JsonResponse({"error": "Invalid JSON"}, status=400)

    def get_device(self, pk: int):
        try:
            device = get_object_or_404(Device, pk=pk)
            return device
        except Exception:
            return JsonResponse({"errors": "Device is not found!"}, status=404)

    def get(self, request, pk: int):
        device = self.get_device(pk)
        return JsonResponse(DeviceOutputSerializer().to_representation(instance=device))

    def put(self, request, pk: int):
        device = self.get_device(pk)
        data, error_response = self.parse_json_request(request.body)
        if error_response:
            return error_response

        schema_version = data.get("schema_version")
        if not schema_version:
            return JsonResponse({"error": "schema_version is required"}, status=400)

        SERIALIZERS = {
            "v1": DeviceCreateV1Serializer,
        }

        SerializerClass = SERIALIZERS.get(schema_version)
        if not SerializerClass:
            return JsonResponse({"error": "Wrong schema_version!"}, status=400)

        serializer = SerializerClass(data=data.get("device"))
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)
        canonical_data = serializer.to_canonical()
        print(canonical_data)
        device = DeviceService.update_device(instance=device, **canonical_data)
        return JsonResponse(
            DeviceOutputSerializer().to_representation(instance=device), status=200
        )

    def patch(self, request, pk: int):
        device = self.get_device(pk)
        data, error_response = self.parse_json_request(request.body)
        if error_response:
            return error_response

        serializer = DeviceUpdateV1Serializer(data=data.get("device"), partial=True)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)

        canonical_data = serializer.to_canonical()
        device = DeviceService.update_device(instance=device, **canonical_data)
        return JsonResponse(
            DeviceOutputSerializer().to_representation(instance=device), status=200
        )

    def delete(self, request, pk: int):
        device = self.get_device(pk)
        DeviceService.delete_device(device)
        return JsonResponse({}, status=204)


@csrf_exempt
@require_http_methods(['POST'])
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
        return None, JsonResponse({'errors': {'json': 'Invalid json.'}}, status=400)

    if not isinstance(payload, (dict, list)):
        return None, JsonResponse(
            {'errors': {'json': 'Payload must be a JSON object or a JSON array.'}},
            status=400,
        )
    return payload, None


def _should_ingest_async(request, payload, *, header_name=None, threshold=None) -> bool:
    if header_name is None:
        header_name = getattr(settings, 'TELEMETRY_ASYNC_HEADER', 'Ingest-Async')
    if threshold is None:
        threshold = getattr(settings, 'TELEMETRY_ASYNC_BATCH_THRESHOLD', 50)

    if request.headers.get(header_name) == '1':
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
    return JsonResponse({'status': 'accepted'}, status=202)


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
        return JsonResponse({'errors': serializer.errors}, status=400)

    total_created = 0
    items = []

    for item in serializer.valid_items:
        result = service(**item)
        total_created += result.created_count
        items.append(
            {
                'created': result.created_count,
                'errors': result.errors,
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
