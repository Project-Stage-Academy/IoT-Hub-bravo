import logging

from models.rule import Rule
from models.event import Event

logger = logging.getLogger(__name__)


class Action:
    def __init__(self):
        pass

    def _notify(self): # underscore??????
        pass

    def _webhook(self): # underscore??????
        pass
    
    def _archieve(self): # underscore??????
        pass
    
    def dispatch_action(self) -> Event:
        logger.info("some action")
        return None


# def dispatch_action(action_name, event):
#     """

#     """

#     if action_name == "notify":
#         logger.info(f"Notify action for event {event.id}")
#     elif action_name == "webhook":
#         logger.info(f"Webhook stub called for event {event.id}")
#     elif action_name == "archive":
#         logger.info(f"Archive action for event {event.id}")
