import logging

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device_metric import DeviceMetric
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator
from apps.rules.utils.rule_engine_utils import map_telemetry_json_to_event, map_telemetry_model_to_event, choose_repository
import redis
from django.conf import settings

redis_client = redis.Redis(**settings.REDIS_CONFIG)

logger = logging.getLogger(__name__)
DEFAULT_DURATION_MINUTES = 5  # default value for time window

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
        
        if isinstance(telemetry, Telemetry):
            mapped_telemetry = map_telemetry_model_to_event(telemetry)
        elif isinstance(telemetry, dict):
            mapped_telemetry = map_telemetry_json_to_event(telemetry)

        device_metrics = DeviceMetric.objects.filter(
            device__serial_id=mapped_telemetry.device_serial_id,
            metric__metric_type=mapped_telemetry.metric_type       
        )
        
        rules = Rule.objects.filter(
            is_active=True,
            device_metric__in=device_metrics
        )
        logger.info("EMMMMMU OTORI")
        logger.warning(f'{telemetry.get("device_serial_id")}')
        logger.warning(f"{mapped_telemetry}")
        for rule in rules:
            condition = rule.condition
            device_metric = rule.device_metric

            duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)
            repository = choose_repository(duration_minutes, redis_client)

            if ConditionEvaluator.evaluate(condition, device_metric, mapped_telemetry, repository):
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

