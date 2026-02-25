import logging
from django.utils import timezone

from apps.rules.models.event import Event
from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry

# Import Prometheus metrics
from apps.common.metrics import events_created_total

logger = logging.getLogger(__name__)


class Action:
    """
    Handles dispatching side-effects for a triggered rule.
    """

    TASKS = (
        "notify_event",
        "deliver_webhook",
    )

    @staticmethod
    def _enqueue(task_name: str, event_id: int) -> None:
        """
        Enqueue Celery task by name.
        Lazy import prevents circular dependency.
        """
        try:
            from apps.rules import tasks

            getattr(tasks, task_name).delay(event_id)
            logger.info(
                "Task enqueued",
                extra={"context": {"task": task_name, "event_id": event_id}},
            )
        except Exception:
            logger.exception(
                "Failed to enqueue task",
                extra={"context": {"task": task_name, "event_id": event_id}},
            )

    @staticmethod
    def dispatch_action(rule: Rule, telemetry: Telemetry) -> Event:
        """
        Create Event and dispatch async side-effects.
        """
        severity = 'info'
        if rule.action and isinstance(rule.action, dict):
            severity = rule.action.get('severity', 'info')

        event = Event.objects.create(
            rule=rule,
            timestamp=timezone.now(),
            trigger_telemetry_id=telemetry.id,
            trigger_device_id=telemetry.device_metric.device_id,
        )

        events_created_total.labels(severity=severity).inc()

        logger.info(
            "Event created",
            extra={
                "context": {
                    "event_id": event.id,
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "trigger_telemetry_id": telemetry.id,
                    "trigger_device_id": telemetry.device_metric.device_id,
                    "severity": severity,
                }
            },
        )

        for task_name in Action.TASKS:
            Action._enqueue(task_name, event.id)

        return event
