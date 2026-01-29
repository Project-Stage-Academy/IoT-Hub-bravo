# devices/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime

from apps.devices.models import Device, Metric, DeviceMetric, Telemetry


@csrf_exempt
def ingest_telemetry(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    required = {"device", "metrics", "ts"}
    if not required.issubset(payload):
        return JsonResponse({"error": "missing fields"}, status=400)

    from django.utils.dateparse import parse_datetime
    ts = parse_datetime(payload["ts"])

    try:
        device = Device.objects.get(serial_id=payload["device"])
    except Device.DoesNotExist:
        return JsonResponse({"error": "device not found"}, status=404)

    created = []

    for name, value in payload["metrics"].items():
        try:
            metric = Metric.objects.get(metric_type=name)
            dm = DeviceMetric.objects.get(device=device, metric=metric)
        except (Metric.DoesNotExist, DeviceMetric.DoesNotExist):
            continue  # або повертати 400, якщо строгий режим

        telemetry = Telemetry(device_metric=dm, ts=ts, value_jsonb={"t": metric.data_type, "v": value})

        telemetry.save()
        created.append(telemetry.id)

    return JsonResponse({"status": "ok", "created": len(created)}, status=201)

