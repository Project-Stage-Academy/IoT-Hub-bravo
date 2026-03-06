import logging
import time

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator

from apps.common.metrics import (
    rules_evaluated_total,
    rules_triggered_total,
    rule_processing_seconds,
)

logger = logging.getLogger(__name__)


class RuleProcessor:
    """
    Processes active rules for a given telemetry and triggers actions if conditions match.
    Collects Prometheus metrics for monitoring rule evaluation performance.
    """

    @staticmethod
    def run(telemetry: Telemetry) -> dict:
        """
        Returns a dict with triggered rules for this telemetry.
        Tracks: rules evaluated, rules triggered, processing time.
        """
        start_time = time.perf_counter()
        results = []

        rules = Rule.objects.filter(is_active=True, device_metric=telemetry.device_metric)

        for rule in rules:
            condition = rule.condition
            device_metric = rule.device_metric
            rule_type = condition.get('type', 'unknown')

            rules_evaluated_total.labels(rule_type=rule_type).inc()

            if ConditionEvaluator.evaluate(condition, device_metric, telemetry):
                rules_triggered_total.labels(rule_type=rule_type).inc()
                Action.dispatch_action(rule, telemetry)
                results.append({"rule_id": rule.id, "triggered": True})
            else:
                results.append({"rule_id": rule.id, "triggered": False})

        rule_processing_seconds.observe(time.perf_counter() - start_time)

        return {"telemetry_id": telemetry.id, "results": results}
