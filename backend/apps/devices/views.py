import json
from django.http import JsonResponse
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
    if not required.issubset(payload) or not isinstance(payload["metrics"], dict):
        return JsonResponse({"error": "invalid payload structure"}, status=400)

    ts = parse_datetime(payload["ts"])

    if ts is None:
        return JsonResponse({"error": "invalid timestamp format."}, status=400)
    
    try:
        device = Device.objects.get(serial_id=payload["device"])
    except Device.DoesNotExist:
        return JsonResponse({"error": "device not found"}, status=404)

    metric_names = list(payload["metrics"].keys())
    device_metrics = {
        dm.metric.metric_type: dm 
        for dm in DeviceMetric.objects.filter(
            device=device, 
            metric__metric_type__in=metric_names
        ).select_related('metric')
    }

    telemetry_instances = []

    for name, value in payload["metrics"].items():
        dm = device_metrics.get(name)
        if not dm:
            continue 
        
        telemetry_instances.append(
            Telemetry(
                device_metric=dm, 
                ts=ts, 
                value_jsonb={"t": dm.metric.data_type, "v": value}
            )
        )
    
    Telemetry.objects.bulk_create(
        telemetry_instances, 
        ignore_conflicts=True
    )

    return JsonResponse({"status": "ok", "created": len(telemetry_instances)}, status=201)
