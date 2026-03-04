import logging
from django.core.cache import caches
from django.conf import settings

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device_metric import DeviceMetric
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator
from apps.rules.utils.rule_engine_utils import map_telemetry_json_to_event, map_telemetry_model_to_event, choose_repository, DEFAULT_DURATION_MINUTES
from common.redis_client import get_redis_client


logger = logging.getLogger(__name__)
redis_client = get_redis_client()
cache_rule = caches["rules"]

class RuleProcessor:
    """
    Processes active rules for a given telemetry and triggers actions if conditions match. 
    """

    @staticmethod
    def run(telemetry: Telemetry | dict) -> dict:
        """
        Returns a dict with triggered rules for this telemetry
        """
        results = []
        window_cache = {}

        if isinstance(telemetry, Telemetry):
            mapped_telemetry = map_telemetry_model_to_event(telemetry)
        elif isinstance(telemetry, dict):
            mapped_telemetry = map_telemetry_json_to_event(telemetry)

        cache_key = f"{mapped_telemetry.device_serial_id}:{mapped_telemetry.metric_type}"

        rules = cache_rule.get(cache_key)
        if rules is None:
            device_metrics = DeviceMetric.objects.filter(
                device__serial_id=mapped_telemetry.device_serial_id,
                metric__metric_type=mapped_telemetry.metric_type
            )
            rules = list(Rule.objects.filter(
                is_active=True,
                device_metric__in=device_metrics
            ).select_related('device_metric__metric'))

            cache_rule.set(cache_key, rules, timeout=settings.RULES_CACHE_TTL)

        for rule in rules:
            condition = rule.condition
            device_metric = rule.device_metric
            duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

            if duration_minutes not in window_cache:
                repository = choose_repository(duration_minutes, redis_client)
                window_cache[duration_minutes] = repository.get_in_window(
                    mapped_telemetry, duration_minutes
                )
            
            cached_window = window_cache[duration_minutes]
                    
            if ConditionEvaluator.evaluate(condition, device_metric, mapped_telemetry, cached_window):
                Action.dispatch_action(rule, mapped_telemetry)
                results.append({"rule_id": rule.id, "triggered": True})
            else:
                results.append({"rule_id": rule.id, "triggered": False})

        return {"telemetry": 
                    {"device_serial_id": mapped_telemetry.device_serial_id,
                     "value": mapped_telemetry.value,
                     "timestamp": mapped_telemetry.timestamp,         
                    }, 
                "results": results}

