import logging
from django.utils import timezone

from apps.rules.models.event import Event

logger = logging.getLogger(__name__)


class Action:
    def _notify(self):
        pass

    def _webhook(self):
        pass
    
    def _archieve(self):
        pass
    
    @staticmethod
    def dispatch_action(rule) -> Event:
        logger.info("create event on action")
        event = Event.objects.create(rule=rule,
                                    timestamp=timezone.now(),
                                    )
        return event
