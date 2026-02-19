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
    Handles actions triggered by rule evaluation.
    Creates Event records and tracks metrics.
    """

    def _notify(self):
        pass

    def _webhook(self):
        pass

    def _archive(self):
        pass

    @staticmethod
    def dispatch_action(rule: Rule, telemetry: Telemetry) -> Event:
        """
        Create an Event when a rule is triggered.
        Tracks event creation metrics by severity.
        """
        logger.info("Create event on action")

        # Get severity from rule action config, default to 'info'
        severity = 'info'
        if rule.action and isinstance(rule.action, dict):
            severity = rule.action.get('severity', 'info')

        event = Event.objects.create(
            rule=rule,
            timestamp=timezone.now(),
            trigger_telemetry_id=telemetry.id,
        )

        # Track event creation
        events_created_total.labels(severity=severity).inc()

        logger.info(
            "Event created",
            extra={
                'event_id': event.id,
                'rule_id': rule.id,
                'severity': severity,
            }
        )

        return event
