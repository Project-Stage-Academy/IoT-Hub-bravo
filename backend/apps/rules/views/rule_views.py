import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from apps.rules.serializers.rule_serializers import RuleCreateSerializer
from apps.rules.services.rule_service import rule_create, rule_put, rule_patch, rule_delete
from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device_metric import DeviceMetric
from apps.users.decorators import jwt_required, role_required
from apps.rules.services.rule_processor import RuleProcessor


logger = logging.getLogger("rules")  # logger.setLevel(logging.INFO) - is default

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(
    role_required(
        {"GET": ["admin","client"], 
         "POST": ["admin","client"], 
         "PUT": ["admin","client"], 
         "PATCH": ["admin","client"], 
         "DELETE": ["admin","client"]}
        ),
        name='dispatch',
)
class RuleView(View):
    def get(self, request, rule_id=None):
        """Get rule(s)"""
        user = request.user
        
        if rule_id:
            try:
                rule = Rule.objects.get(id=rule_id, device_metric__device__user=user)
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
                return JsonResponse({"error": "Rule not found"}, status=404)
        else:
            try:
                limit = int(request.GET.get("limit", 20))
                offset = int(request.GET.get("offset", 0))
            except ValueError:
                raise ValueError("Limit and offset must be integer type")
            
            if limit <= 0 or offset < 0:
                return JsonResponse({"error": "Limit must be > 0 and offset must be >= 0"}, status=400)
            
            all_rules = Rule.objects.filter(device_metric__device__user=user)
            total = all_rules.count()
            rules = all_rules[offset : offset + limit]
            data = [{"id": r.id, 
                    "name": r.name,
                    "device_metric_id": r.device_metric.id,
                    "description": r.description, 
                    "condition": r.condition, 
                    "action": r.action,
                    "is_active": r.is_active,
                    } for r in rules]
            return JsonResponse({"total": total, "limit": limit, "offset": offset, "items": data})
        

    def post(self, request, ):
        """Create a new rule"""
        data = json.loads(request.body)
        user = request.user

        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        # check if user have that device_metrics
        device_metric_id = serializer.validated_data.get("device_metric")
        if not DeviceMetric.objects.filter(id=device_metric_id, device__user=user).exists():
            return JsonResponse({"error": "DeviceMetric does not belong to the user"}, status=403)
        
        rule = rule_create(rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})


    def put(self, request, rule_id):
        """Full update"""
        data = json.loads(request.body)
        user = request.user
        
        try:
            rule = Rule.objects.get(id=rule_id, device_metric__device__user=user)
        except Rule.DoesNotExist:
            return JsonResponse({"error": "Rule not found or access denied"}, status=404)
        
        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        rule = rule_put(rule_id=rule_id, rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})


    def patch(self, request, rule_id):
        """Partial update"""
        data = json.loads(request.body)
        user = request.user
        
        try:
            rule = Rule.objects.get(id=rule_id, device_metric__device__user=user)
        except Rule.DoesNotExist:
            return JsonResponse({"error": "Rule not found or access denied"}, status=404)
        
        serializer = RuleCreateSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        rule = rule_patch(rule_id=rule_id, rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})


    def delete(self, request, rule_id):
        """Delete rule"""
        user = request.user
        
        try:
            rule = Rule.objects.get(id=rule_id, device_metric__device__user=user)
        except Rule.DoesNotExist:
            return JsonResponse({"error": "Rule not found or access denied"}, status=404)
        
        rule_delete(rule_id=rule_id)
        return JsonResponse({"status": "ok", "message": "deleted"})


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(
    role_required({"POST": ["admin", "client"]}),
    name='dispatch'
)
class RuleEvaluateView(View):
    def post(self, request):
        user = request.user

        last_telemetries = (
            Telemetry.objects
            .filter(device_metric__device__user=user)
            .order_by('device_metric', '-created_at')
            .distinct('device_metric')
        )

        results = []

        for telemetry in last_telemetries:
            try:
                evaluation_result = RuleProcessor.run(telemetry)

                results.append({
                    "telemetry_id": telemetry.id,
                    "device_metric_id": telemetry.device_metric.id,
                    "device_name": telemetry.device_metric.device.name,
                    "result": evaluation_result
                })
            except Exception as e:
                logger.warning(f"Failed to evaluate telemetry {telemetry.id}: {e}")
                results.append({
                    "telemetry_id": telemetry.id,
                    "error": str(e)
                })

        return JsonResponse({"status": "ok", "results": results})