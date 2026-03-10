import logging
from typing import Union
from django.db import transaction
from apps.rules.models.event_delivery import EventDelivery, DeliveryType
from apps.rules.tasks import process_delivery_task
from django.core.exceptions import ValidationError
from django.db import DatabaseError

logger = logging.getLogger(__name__)


class EventNotificationHandler:
    def handle(self, payload: Union[dict, list[dict]]) -> None:
        if isinstance(payload, list):
            for item in payload:
                self._process_single(item)
        else:
            self._process_single(payload)

    def _process_single(self, data: dict) -> None:
        """Processes a single event payload, creating EventDelivery records for enabled actions and dispatching them to Celery."""
        """NOTE: Unvalid messages should not olny be logged but also sent to a dead-letter queue for later analysis. This is a TODO for future improvement."""

        try:
            event_uuid = data['event_uuid']
            rule_id = data['rule_id']
            device_serial_id = data['trigger_device_serial_id']

            action = data.get('action', {})

            if not action:
                return

            with transaction.atomic():

                webhook_data = action.get('webhook', {})
                if webhook_data and webhook_data.get('enabled'):
                    self._create_and_dispatch(
                        event_uuid, rule_id, device_serial_id, DeliveryType.WEBHOOK, webhook_data
                    )

                notification_data = action.get('notification', {})
                if notification_data and notification_data.get('enabled'):
                    self._create_and_dispatch(
                        event_uuid,
                        rule_id,
                        device_serial_id,
                        DeliveryType.NOTIFICATION,
                        notification_data,
                    )

        except KeyError as ke:
            logger.error('Missing required field %s in payload: %s', ke, data)
        except (ValueError, TypeError, ValidationError) as ve:
            logger.error('Data validation failed for payload %s: %s', data, ve)
        except DatabaseError as dbe:
            logger.exception('Database connection error: %s', dbe)
            raise
        except Exception:
            logger.exception('Failed to process notifications for Event.')
            raise

    def _create_and_dispatch(self, event_uuid, rule_id, device_serial, delivery_type, payload):
        """Creates a DB record and immediately dispatches it to Celery"""

        delivery, created = EventDelivery.objects.get_or_create(
            event_uuid=event_uuid,
            delivery_type=delivery_type,
            defaults={
                'rule_id': rule_id,
                'trigger_device_serial_id': device_serial,
                'payload': payload,
                'max_attempts': 5,
            },
        )

        if created:
            logger.info(
                f"Created {delivery_type} delivery {delivery.id} for Event {event_uuid}. Preparing dispatch..."
            )

            transaction.on_commit(lambda: process_delivery_task.delay(delivery.id))
        else:
            logger.debug(
                f"{delivery_type} delivery for Event {event_uuid} already exists. "
                "Skipping duplicate Celery dispatch."
            )
