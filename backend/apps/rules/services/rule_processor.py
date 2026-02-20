import logging

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class RuleProcessor:
    """
    Processes active rules for a given telemetry and triggers actions if conditions match.
    """

    @staticmethod
    def run(telemetry: Telemetry) -> dict:
        """
        Returns a dict with triggered rules for this telemetry
        """
        results = []

        rules = Rule.objects.filter(is_active=True, device_metric=telemetry.device_metric)

        for rule in rules:
        
            condition = rule.condition
            device_metric = rule.device_metric

            if ConditionEvaluator.evaluate(condition, device_metric, telemetry):
                Action.dispatch_action(rule, telemetry)
                results.append({
                    "rule_id": rule.id,
                    "triggered": True
                })
            else:
                results.append({
                    "rule_id": rule.id,
                    "triggered": False
                })

        return {
            "telemetry_id": telemetry.id,
            "results": results
        }
