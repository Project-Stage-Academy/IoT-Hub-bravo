from django.utils import timezone
from celery import shared_task

from models.rule import Rule
from models.event import Event
from action import Action


def evaluate_condition(condition, telemetry):
    """
    simple evaluator
    condition = {"metric": "temperature", "operator": ">", "value": 100}
    """
    for item in telemetry:
        metric = item.get(condition["metric"])
        if metric is None:
            continue
        op = condition["operator"]
        val = condition["value"]
        if op == ">" and metric > val:
            return True
        if op == "<" and metric < val:
            return True
        if op == "==" and metric == val:
            return True
    return False


class RuleProcessor:
    """
    """

    def run(self, telemetry):
        rules = Rule.objects.filter(is_active=True)

        for rule in rules:
            if rule.device_metric.device.user != telemetry.device.user:
                continue

            if evaluate_condition(rule.condition, telemetry):
                event = Event.objects.create(
                    rule=rule,
                    timestamp=timezone.now()
                )
                Action.dispatch_action(rule.action, event)

@shared_task
def run_rule_processor_task(telemetry):
    RuleProcessor().run(telemetry)