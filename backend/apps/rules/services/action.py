import logging
from django.utils import timezone

from apps.rules.models.event import Event
from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry

logger = logging.getLogger(__name__)


class Action:
    def _notify(self):
        pass

    def _webhook(self):
        pass

    def _archieve(self):
        pass

    @staticmethod
    def dispatch_action(rule: Rule, telemetry: Telemetry) -> Event:
        logger.info("Create event on action")
        event = Event.objects.create(
            rule=rule,
            timestamp=timezone.now(),
            trigger_telemetry=telemetry,
        )
        return event
