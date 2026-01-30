from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import Device
from .serializers.device_serializer import DeviceSerializer
import json

def get_devices():
    devices = Device.objects.filter(is_active=True)
    data = [
            DeviceSerializer(instance=d).to_representation(d)
            for d in devices
    ]
    return JsonResponse(data, safe=False)

def create_device(body):
    try:
        data_from_json = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    serializer = DeviceSerializer(data = data_from_json)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)

    device = serializer.create()
    return JsonResponse(
        serializer.to_representation(device),
        status=201
    )
    
@csrf_exempt
def list_devices(request):
    if request.method == "GET":
        return get_devices()
    elif request.method == "POST":
        return create_device(request.body)
    else:
        return HttpResponseNotAllowed(["GET", "POST"])

@csrf_exempt
def device_detail(request, pk):
    device = get_object_or_404(Device, pk=pk)

    if request.method == "GET":
        data = DeviceSerializer().to_representation(device)
        return JsonResponse(data)

    elif request.method == "PATCH":
        try:
            data_from_json = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        serializer = DeviceSerializer(instance = device, data = data_from_json, partial = True)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)
        device = serializer.update(device)
        return JsonResponse(serializer.to_representation(device),status=200)
    elif request.method == "PUT":
        try:
            data_from_json = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        serializer = DeviceSerializer(instance = device, data = data_from_json)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)
        device = serializer.update(device)
        return JsonResponse(serializer.to_representation(device), status = 200)
    elif request.method == "DELETE":
        device.delete()
        return JsonResponse({"message": "Device deleted"}, status=204)

    else:
        return HttpResponseNotAllowed(["GET", "PATCH", "PUT", "DELETE"])
