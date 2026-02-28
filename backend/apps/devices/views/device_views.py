import json

from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.views import View

from apps.devices.models import Device
from apps.users.decorators import jwt_required, role_required
from apps.devices.serializers.device_serializers.base_device_serializer import (
    DeviceOutputSerializer,
)
from apps.devices.serializers.device_serializers.create_device_serializer import (
    DeviceCreateV1Serializer,
)
from apps.devices.serializers.device_serializers.update_device_serializer import (
    DeviceUpdateV1Serializer,
)
from apps.devices.services.device_service import DeviceService


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(jwt_required, name="dispatch")
@method_decorator(
    role_required({"GET": ["client", "admin"], "POST": ["admin"]}), name="dispatch"
)
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
            return JsonResponse(
                {"error": "limit and offset must be integers"}, status=400
            )

        if limit <= 0:
            return JsonResponse({"error": "Limit must be greater than 0"}, status=400)
        if offset < 0:
            return JsonResponse(
                {"error": "Offset must be positive integer"}, status=400
            )
        devices_qs = Device.objects.select_related("user").all().order_by("id")
        total = devices_qs.count()
        devices = devices_qs[offset : offset + limit]
        data = [DeviceOutputSerializer().to_representation(instance=d) for d in devices]
        return JsonResponse(
            {"total": total, "limit": limit, "offset": offset, "items": data}
        )

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


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(jwt_required, name="dispatch")
@method_decorator(
    role_required(
        {
            "GET": ["client", "admin"],
            "PUT": ["admin"],
            "PATCH": ["admin"],
            "DELETE": ["admin"],
        }
    ),
    name="dispatch",
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
