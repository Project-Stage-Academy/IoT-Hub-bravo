from typing import Union
import logging
from apps.rules.models.event import Event
from django.core.exceptions import ValidationError
from django.db import DatabaseError

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
        """Processes a single event payload, creating an Event record in the database."""
        """NOTE: Unvalid messages should not olny be logged but also sent to a dead-letter queue for later analysis. This is a TODO for future improvement."""

        try:
            event_uuid = data['event_uuid']

            event, created = Event.objects.get_or_create(
                event_uuid=event_uuid,
                defaults={
                    'rule_triggered_at': data['rule_triggered_at'],
                    'rule_id': data['rule_id'],
                    'acknowledged': False,
                    'trigger_device_serial_id': data['trigger_device_serial_id'],
                    'trigger_context': data.get('trigger_context', {}),
                },
            )
            if created:
                logger.info('Successfully created Event with UUID %s', event_uuid)
            else:
                logger.debug('Event with UUID %s already exists. Skipping creation.', event_uuid)
        except KeyError as ke:
            logger.error('Missing required field %s in payload: %s', ke, data)
        except (ValueError, TypeError, ValidationError) as ve:
            logger.error('Data validation failed for payload %s: %s', data, ve)
        except DatabaseError as dbe:
            logger.exception('Database connection error: %s', dbe)
            raise
        except Exception as e:
            logger.exception('Failed to save Event to database for payload %s: %s', data, e)
            raise
