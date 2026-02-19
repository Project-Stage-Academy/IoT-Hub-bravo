import logging
import time

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator

# Import Prometheus metrics
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
    def run(telemetry: Telemetry):
        """
        Evaluate all active rules for the given telemetry.
        Tracks: rules evaluated, rules triggered, processing time.
        """
        start_time = time.perf_counter()

        rules = Rule.objects.filter(is_active=True, device_metric=telemetry.device_metric)

        for rule in rules:
            condition = rule.condition
            device_metric = rule.device_metric
            rule_type = condition.get('type', 'unknown')

            # Track rule evaluation
            rules_evaluated_total.labels(rule_type=rule_type).inc()

            if ConditionEvaluator.evaluate(condition, device_metric, telemetry):
                # Track triggered rule
                rules_triggered_total.labels(rule_type=rule_type).inc()
                Action.dispatch_action(rule, telemetry)

        # Track total processing time
        processing_time = time.perf_counter() - start_time
        rule_processing_seconds.observe(processing_time)
