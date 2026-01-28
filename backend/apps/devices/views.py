# devices/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime

from apps.devices.models import Device, Metric, DeviceMetric, Telemetry


@csrf_exempt
def ingest_telemetry(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    payload = json.loads(request.body)

    device = Device.objects.get(serial_id=payload["device"])

    for m in payload["metrics"]:
        metric, _ = Metric.objects.get_or_create(
            metric_type=m["metric"],
            defaults={"data_type": m["t"]},
        )

        dm, _ = DeviceMetric.objects.get_or_create(
            device=device,
            metric=metric,
        )

        Telemetry.objects.create(
            device_metric=dm,
            value_jsonb={"t": m["t"], "v": m["v"]},
            ts=parse_datetime(payload["ts"]),
        )

    return JsonResponse({"status": "ok"})
