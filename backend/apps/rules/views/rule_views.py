import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from apps.rules.serializers.rule_serializers import RuleCreateSerializer
from apps.rules.services.rule_service import rule_create, rule_put, rule_patch, rule_delete
from apps.rules.models.rule import Rule
from apps.users.decorators import jwt_required, role_required


logger = logging.getLogger("rules")  # logger.setLevel(logging.INFO) - is default

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(jwt_required, name='dispatch')
@method_decorator(
    role_required(
        {"GET": ["client", "admin"], 
         "POST": ["admin","client"], 
         "PUT": ["admin","client"], 
         "PATCH": ["admin","client"], 
         "DELETE": ["admin","client"]}
        ),
        name='dispatch',
)
class RuleView(View):
    def post(self, request):
        """Create a new rule"""
        data = json.loads(request.body)

        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        rule = rule_create(rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})

    def put(self, request, rule_id):
        """Full update"""
        data = json.loads(request.body)

        serializer = RuleCreateSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        rule = rule_put(rule_id=rule_id, rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})

    def patch(self, request, rule_id):
        """Partial update"""
        data = json.loads(request.body)

        serializer = RuleCreateSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)
        
        rule = rule_patch(rule_id=rule_id, rule_data=serializer.validated_data)
        return JsonResponse({"status": "ok", "rule_id": rule.id})

    def delete(self, request, rule_id):
        """Delete rule"""
        rule_delete(rule_id=rule_id)
        return JsonResponse({"status": "ok", "message": "deleted"})

    def get(self, request, rule_id=None):
        """Get rule(s)"""
        if rule_id:
            try:
                rule = Rule.objects.get(id=rule_id)
                data = {
                    "id": rule.id,
                    "name": rule.name,
                    "condition": rule.condition,
                    "action": rule.action,
                    "is_active": rule.is_active
                }
                return JsonResponse({"rule": data})
            except Rule.DoesNotExist:
                return JsonResponse({"error": "Rule not found"}, status=404)
        else:
            rules = Rule.objects.all()
            data = [{"id": r.id, "name": r.name} for r in rules]
            return JsonResponse({"rules": data})