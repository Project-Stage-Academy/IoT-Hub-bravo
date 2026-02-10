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
    def run(telemetry: Telemetry):
        rules = Rule.objects.filter(is_active=True, device_metric=telemetry.device_metric)

        for rule in rules:
            if ConditionEvaluator.evaluate(rule, telemetry):
                Action.dispatch_action(rule, telemetry)
