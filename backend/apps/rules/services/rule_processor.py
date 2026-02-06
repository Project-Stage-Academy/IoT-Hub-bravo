from django.utils import timezone
from celery import shared_task

from models.rule import Rule
from models.event import Event
from action import Action
from condition_evaluator import ConditionEvaluator


class RuleProcessor:
    """
    """

    def run(self, telemetry):
        rules = Rule.objects.filter(is_active=True)

        for rule in rules:
            if rule.device_metric.device.user != telemetry.device.user:
                continue
            if ConditionEvaluator.evaluate_condition(rule.condition, telemetry):
                event = Event.objects.create(rule=rule,
                                            timestamp=timezone.now(),
                                            )
                Action.dispatch_action(rule.action, event)
                

@shared_task
def run_rule_processor_task(telemetry):
    RuleProcessor().run(telemetry)