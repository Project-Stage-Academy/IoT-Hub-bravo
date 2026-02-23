import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.rules.serializers.rule_serializers import RuleCreateSerializer, RulePatchSerializer
from apps.rules.services.rule_service import rule_create, rule_put, rule_patch, rule_delete
from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device import Device
from apps.devices.models.device_metric import DeviceMetric
from apps.users.decorators import jwt_required, role_required
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.utils.views_utils import parse_json_request


logger = logging.getLogger("rules")


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(
    role_required(
        {
            "GET": ["admin", "client"],
            "POST": ["admin", "client"],
            "PUT": ["admin", "client"],
            "PATCH": ["admin", "client"],
            "DELETE": ["admin", "client"],
        }
    ),
    name='dispatch',
)
class RuleView(View):
    def get(self, request, rule_id=None):
        """Get rule(s)"""
        user = request.user
        is_admin = user.role == "admin"

        if rule_id:
            try:
                rule = (
                    Rule.objects.get(id=rule_id)
                    if is_admin
                    else Rule.objects.get(id=rule_id, device_metric__device__user=user)
                )
                data = {
                    "id": rule.id,
                    "name": rule.name,
                    "device_metric_id": rule.device_metric.id,
                    "description": rule.description,
                    "condition": rule.condition,
                    "action": rule.action,
                    "is_active": rule.is_active,
                }
                return JsonResponse({"rule": data})
            except Rule.DoesNotExist:
                return JsonResponse({"code": 404, "message": "Rule not found"}, status=404)
        else:
            try:
                limit = int(request.GET.get("limit", 20))
                offset = int(request.GET.get("offset", 0))
            except ValueError:
                    return JsonResponse(
                        {"code": 400, "message": "Limit and offset must be integer type"},
                        status=400
                    )

            if limit <= 0 or offset < 0:
                return JsonResponse(
                    {"code": 400, "message": "Limit must be > 0 and offset must be >= 0"},
                    status=400,
                )

            all_rules = (
                Rule.objects.all()
                if is_admin
                else Rule.objects.filter(device_metric__device__user=user)
            )
            total = all_rules.count()
            rules = all_rules[offset : offset + limit]
            data = [
                {
                    "id": r.id,
                    "name": r.name,
                    "device_metric_id": r.device_metric.id,
                    "description": r.description,
                    "condition": r.condition,
                    "action": r.action,
                    "is_active": r.is_active,
                }
                for r in rules
            ]
            return JsonResponse({"total": total, "limit": limit, "offset": offset, "items": data})

    def post(self, request):
        """Create a new rule"""
        data = parse_json_request(request.body)
        if isinstance(data, JsonResponse): # JSON parsing error, return response
            return data
        user = request.user
        is_admin = user.role == "admin"

        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse(
                {"code": 400, "message": serializer.errors}, status=400
            )

        # check if user has that device_metrics
        device_metric_id = serializer.validated_data.get("device_metric_id")
        if (
            not is_admin
            and not DeviceMetric.objects.filter(id=device_metric_id, device__user=user).exists()
        ):
            return JsonResponse(
                {"code": 403, "message": "DeviceMetric does not belong to the user"}, status=403
            )

        rule = rule_create(rule_data=serializer.validated_data)
        data = {
            "id": rule.id,
            "name": rule.name,
            "device_metric_id": rule.device_metric.id,
            "description": rule.description,
            "condition": rule.condition,
            "action": rule.action,
            "is_active": rule.is_active,
        }
        return JsonResponse(data, status=201)

    def put(self, request, rule_id):
        """Full update"""
        data = parse_json_request(request.body)
        if isinstance(data, JsonResponse): # JSON parsing error, return response
            return data
        user = request.user
        is_admin = user.role == "admin"

        try:
            rule = (
                Rule.objects.get(id=rule_id)
                if is_admin
                else Rule.objects.get(id=rule_id, device_metric__device__user=user)
            )
        except Rule.DoesNotExist:
            return JsonResponse({"code": 404, "message": "Rule not found"}, status=404)

        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse(
                {"code": 400, "message": serializer.errors}, status=400
            )

        rule = rule_put(rule_id=rule_id, rule_data=serializer.validated_data)
        data = {
            "id": rule.id,
            "name": rule.name,
            "device_metric_id": rule.device_metric.id,
            "description": rule.description,
            "condition": rule.condition,
            "action": rule.action,
            "is_active": rule.is_active,
        }
        return JsonResponse(data, status=200)

    def patch(self, request, rule_id):
        """Partial update"""
        data = parse_json_request(request.body)
        if isinstance(data, JsonResponse): # JSON parsing error, return response
            return data
        user = request.user
        is_admin = user.role == "admin"

        try:
            rule = (
                Rule.objects.get(id=rule_id)
                if is_admin
                else Rule.objects.get(id=rule_id, device_metric__device__user=user)
            )
        except Rule.DoesNotExist:
            return JsonResponse({"code": 404, "message": "Rule not found"}, status=404)

        serializer = RulePatchSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({"code": 400, "message": serializer.errors}, status=400)

        rule = rule_patch(rule_id=rule_id, rule_data=serializer.validated_data)
        return JsonResponse({"status": 200, "rule_id": rule.id}, status=200)

    def delete(self, request, rule_id):
        """Delete rule"""
        user = request.user
        is_admin = user.role == "admin"

        try:
            (
                Rule.objects.get(id=rule_id)
                if is_admin
                else Rule.objects.get(id=rule_id, device_metric__device__user=user)
            )
        except Rule.DoesNotExist:
            return JsonResponse({"code": 404, "message": "Rule not found"}, status=404)

        rule_delete(rule_id=rule_id)
        return JsonResponse({}, status=204)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(role_required({"POST": ["admin", "client"]}), name='dispatch')
class RuleEvaluateView(View):
    def post(self, request):
        user = request.user
        data = parse_json_request(request.body)
        if isinstance(data, JsonResponse): # JSON parsing error, return response
            return data
        device_id = data.get("device_id")
        device_metric_id = data.get("device_metric_id")
        is_admin = user.role == "admin"

        qs = (
            Telemetry.objects.all()
            if is_admin
            else Telemetry.objects.filter(device_metric__device__user=user)
        )

        if device_id is not None:
            if not Device.objects.filter(id=device_id).exists():
                return JsonResponse({"code": 404, "message": "Device not found"}, status=404)

            if not is_admin and not Device.objects.filter(id=device_id, user=user).exists():
                return JsonResponse({"code": 403, "message": "Access denied"}, status=403)
            qs = qs.filter(device_metric__device_id=device_id)

        if device_metric_id is not None:
            if not DeviceMetric.objects.filter(id=device_metric_id).exists():
                return JsonResponse({"code": 404, "message": "DeviceMetric not found"}, status=404)

            if (
                not is_admin
                and not DeviceMetric.objects.filter(
                    id=device_metric_id, device__user=user
                ).exists()
            ):
                return JsonResponse({"code": 403, "message": "Access denied"}, status=403)
            qs = qs.filter(device_metric_id=device_metric_id)

        if device_id is not None and device_metric_id is not None:
            if not DeviceMetric.objects.filter(id=device_metric_id, device_id=device_id).exists():
                return JsonResponse(
                    {"code": 400, "message": "DeviceMetric does not belong to this Device"},
                    status=400,
                )

        last_telemetries = qs.order_by('device_metric', '-created_at').distinct('device_metric')

        results = []
        for telemetry in last_telemetries:
            evaluation_result = RuleProcessor.run(telemetry)
            results.append(
                {
                    "telemetry_id": telemetry.id,
                    "device_metric_id": telemetry.device_metric.id,
                    "device_name": telemetry.device_metric.device.name,
                    "result": evaluation_result,
                }
            )

        return JsonResponse({"status": 200, "results": results})
