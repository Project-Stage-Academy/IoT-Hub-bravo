# Create your views here.
# views.py
import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime

from .models import Telemetry, DeviceMetric, Metric


@csrf_exempt
def ingest_telemetry(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    required = {"schema_version", "device_metric_id", "ts", "value"}
    if not required.issubset(payload):
        return JsonResponse({"error": "missing fields"}, status=400)

    ts = parse_datetime(payload["ts"])
    if ts is None:
        return JsonResponse({"error": "invalid timestamp"}, status=400)

    try:
        device_metric = DeviceMetric.objects.select_related(
            "metric"
        ).get(id=payload["device_metric_id"])
    except DeviceMetric.DoesNotExist:
        return JsonResponse({"error": "device_metric not found"}, status=404)

    metric = device_metric.metric

    telemetry = Telemetry(
        device_metric=device_metric,
        ts=ts,
        value_jsonb={"value": payload["value"]},
    )

    if metric.data_type == "numeric":
        telemetry.value_numeric = payload["value"]
    elif metric.data_type == "boolean":
        telemetry.value_bool = payload["value"]
    elif metric.data_type == "str":
        telemetry.value_str = payload["value"]

    telemetry.save()

    return JsonResponse(
        {
            "status": "ok",
            "telemetry_id": telemetry.id,
        },
        status=201,
    )
