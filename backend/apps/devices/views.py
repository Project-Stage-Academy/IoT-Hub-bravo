from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from apps.users.decorators import jwt_required, role_required

from .models import Device
from .serializers.device_serializer import DeviceSerializer
from .services.device_service import DeviceService

import json


def get_devices(limit: int, offset: int):
    if limit <= 0:
        return JsonResponse({"error": "Limit must be greater than 0"}, status=400)
    if offset < 0:
        return JsonResponse({"error": "Offset must be positive integer"}, status=400)

    devices_qs = Device.objects.all().order_by("id")
    total = devices_qs.count()
    devices = devices_qs[offset:offset + limit]

    data = [DeviceSerializer(instance=d).to_representation(d) for d in devices]
    return JsonResponse({
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": data
    })

def parse_json_request(body: bytes):
    try:
        return json.loads(body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@jwt_required
@role_required({
    "GET": ["client", "admin"],
    "POST": "admin"
})
def list_devices(request):
    if request.method == "GET":
        try:
            limit = int(request.GET.get("limit", 5))
            offset = int(request.GET.get("offset", 0))
        except ValueError:
            return JsonResponse({"error": "limit and offset must be integers"}, status=400)

        return get_devices(limit, offset)

    elif request.method == "POST":
        data, error_response = parse_json_request(request.body)
        if error_response:
            return error_response

        serializer = DeviceSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)

        device = DeviceService.create_device(serializer.validated_data)
        return JsonResponse(serializer.to_representation(device), status=201)

    else:
        return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
@jwt_required
@role_required({
    "GET": ["client", "admin"],
    "PUT": "admin",
    "PATCH": "admin",
    "DELETE": "admin"
})
def device_detail(request, pk: int):
    device = get_object_or_404(Device, pk=pk)

    if request.method == "GET":
        return JsonResponse(DeviceSerializer(instance=device).to_representation(device))

    data, error_response = None, None
    if request.method in ["PATCH", "PUT"]:
        data, error_response = parse_json_request(request.body)
        if error_response:
            return error_response

    if request.method == "PATCH":
        serializer = DeviceSerializer(instance=device, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)

        device = DeviceService.update_device(device, serializer.validated_data)
        return JsonResponse(serializer.to_representation(device), status=200)

    elif request.method == "PUT":
        serializer = DeviceSerializer(instance=device, data=data)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)

        device = DeviceService.update_device(device, serializer.validated_data)
        return JsonResponse(serializer.to_representation(device), status=200)

    elif request.method == "DELETE":
        DeviceService.delete_device(device)
        return JsonResponse({"message": "Device deleted"}, status=204)

    else:
        return HttpResponseNotAllowed(["GET", "PATCH", "PUT", "DELETE"])
