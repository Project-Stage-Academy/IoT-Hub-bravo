from typing import Union
import logging
from apps.rules.models.event import Event

logger = logging.getLogger(__name__) 

class EventDBHandler:
    """
    Class resonsible for parsing JSON payloads from rule engine and creating Event objects in the database.
    """

    def handle(self, payload: Union[dict, list[dict]]) -> None:
        if isinstance(payload, list):
            for item in payload:
                self._process_single(item)
        else:
            self._process_single(payload)
    
    def _process_single(self, data: dict) -> None:
        try:
            event_uuid = data['event_uuid']

            ecent, created = Event.objects.get_or_create(
                id=event_uuid,
                defaults={
                    'rule_triggered_at': data['rule_triggered_at'],
                    'rule_id': data['rule_id'],
                    'acknowledged': False,
                    'trigger_device_serial_id': data['trigger_device_serial_id'],
                    'trigger_context': data.get('trigger_context', {}),
                }
            )
            if created:
                logger.info('Successfully created Event with UUID %s', event_uuid)
            else:
                logger.debug('Event with UUID %s already exists. Skipping creation.', event_uuid)
        except KeyError as ke:
            logger.error('Missing required field %s in payload: %s', ke, data)
        except Exception as e:
            logger.exception('Failed to save Event to database for payload %s: %s', data, e)
            raise
