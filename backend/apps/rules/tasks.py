from celery import shared_task
from celery.utils.log import get_task_logger

from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor
import requests
from apps.rules.models.event_delivery import EventDelivery, Status, DeliveryType
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

logger_celery = get_task_logger(__name__)


@shared_task(name="check_system_status")
def check_system_status():
    """Test example"""
    logger_celery.info("--- CELERY BEAT IS WORKING: System status checked! ---")
    return "Success"


@shared_task(name="run_rule_processor")
def run_rule_processor(telemetry_id: int):
    """
    Celery task to run RuleProcessor asynchronously on the given telemetry
    """
    try:
        telemetry = Telemetry.objects.get(id=telemetry_id)
    except Telemetry.DoesNotExist:
        logger_celery.warning("Telemetry not found", extra={"telemetry_id": telemetry_id})

    RuleProcessor.run(telemetry)


# @shared_task(
#     name="notify_event",
# )
# def notify_event(event_id: int):
#     """
#     Simple notification task: logs the event firing. Could be extended to persist
#     notifications or push to a user-notification service.
#     """
#     try:
#         event = Event.objects.select_related('rule').get(id=event_id)
#     except Event.DoesNotExist:
#         logger_celery.warning("notify_event: Event not found", extra={"event_id": event_id})
#         return

#     payload = {
#         "event_uuid": str(event.event_uuid),
#         "rule_id": event.rule.id,
#         "rule_name": event.rule.name,
#         "trigger_device_serial_id": event.trigger_device_serial_id,
#         "trigger_context": event.trigger_context,
#         "rule_triggered_at": event.rule_triggered_at.isoformat(),
#     }

#     logger_celery.info("Event notification enqueued", extra={"notification": payload})


# @shared_task(
#     bind=True,
#     name="deliver_webhook",
#     autoretry_for=(RequestException,),
#     retry_backoff=True,
#     retry_backoff_max=60,
#     retry_jitter=True,
#     retry_kwargs={"max_retries": 5},
# )
# def deliver_webhook(self, event_id: int):
#     """
#     Deliver a webhook for the given event. Will retry on network errors.

#     Safe default: will NOT perform external HTTP calls unless
#     `settings.RULES_ALLOW_WEBHOOKS` is True.
#     """
#     try:
#         event = Event.objects.select_related('rule').get(id=event_id)
#     except Event.DoesNotExist:
#         logger_celery.warning("deliver_webhook: Event not found", extra={"event_id": event_id})
#         return

#     if not getattr(settings, 'RULES_ALLOW_WEBHOOKS', False):
#         logger_celery.info("Webhook delivery disabled by settings", extra={"event_id": event_id})
#         return

#     actions = event.rule.action or {}
#     webhook_cfg = actions.get("webhook") or {}

#     if not webhook_cfg.get("enabled"):
#         logger_celery.info("Webhook disabled for rule", extra={"rule_id": event.rule_id})
#         return

#     resolved_url = webhook_cfg.get("url")
#     if not resolved_url:
#         logger_celery.warning("Webhook enabled but url missing", extra={"rule_id": event.rule_id})
#         return

#     body = {
#         "event_uuid": str(event.event_uuid),
#         "rule_id": event.rule.id,
#         "rule_name": event.rule.name,
#         "trigger_device_serial_id": event.trigger_device_serial_id,
#         "trigger_context": event.trigger_context,
#         "rule_triggered_at": event.rule_triggered_at.isoformat(),
#     }

#     headers = {"Content-Type": "application/json"}

#     try:
#         resp = requests.post(resolved_url, json=body, headers=headers, timeout=10)
#         if not (200 <= resp.status_code < 300):
#             logger_celery.warning(
#                 "Webhook delivery failed (status)",
#                 extra={"status": resp.status_code, "url": resolved_url, "event_uuid": str(event.event_uuid)},
#             )
#             raise RequestException(f"Non-2xx response: {resp.status_code}")

#         logger_celery.info("Webhook delivered", extra={"url": resolved_url, "event_uuid": str(event.event_uuid)})
#     except RequestException as exc:
#         logger_celery.warning(
#             "Webhook delivery error, will retry", extra={"error": str(exc), "event_uuid": str(event.event_uuid)}
#         )
#         raise
# bind=True обов'язково потрібен, щоб ми мали доступ до об'єкта таски (self)
# і могли викликати self.retry().
# max_retries=None, бо ми будемо контролювати ліміт спроб через поле max_attempts у БД.

@shared_task(bind=True, max_retries=None)
def process_delivery_task(self, delivery_id: int):
    """Asynchronous task to process an EventDelivery (webhook or notification) with retry logic and status updates in the database."""
    try:
        delivery = EventDelivery.objects.get(id=delivery_id)
    except EventDelivery.DoesNotExist:
        logger_celery.error("EventDelivery %s not found. Dropping task.", delivery_id)
        return

    if delivery.status == Status.SUCCESS:
        logger_celery.info("Delivery %s already successful. Skipping.", delivery_id)
        return

    if delivery.attempts >= delivery.max_attempts:
        logger_celery.warning("Delivery %s reached max attempts. Skipping.", delivery_id)
        return

    delivery.status = Status.PROCESSING
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()
    delivery.save(update_fields=['status', 'attempts', 'last_attempt_at', 'updated_at'])

    try:
        if delivery.delivery_type == DeliveryType.WEBHOOK:
            _process_webhook(delivery)
        elif delivery.delivery_type == DeliveryType.NOTIFICATION:
            _process_notification(delivery)
        else:
            raise ValueError(f"Unknown delivery type: {delivery.delivery_type}")

        delivery.status = Status.SUCCESS
        delivery.error_message = None
        delivery.save(update_fields=['status', 'response_status', 'error_message', 'updated_at'])
        
        logger_celery.info("Delivery %s completed successfully.", delivery_id)

    except Exception as exc:
        logger_celery.warning("Delivery %s failed on attempt %s: %s", delivery_id, delivery.attempts, exc)
        
        delivery.error_message = str(exc)
        
        if delivery.attempts >= delivery.max_attempts:
            delivery.status = Status.REJECTED
            delivery.save(update_fields=['status', 'error_message', 'updated_at'])
            logger_celery.error("Delivery %s REJECTED after %s attempts.", delivery_id, delivery.max_attempts)
        else:
            delivery.status = Status.RETRY
            
            delay_seconds = (2 ** delivery.attempts) * 20
            
            delivery.next_retry_at = timezone.now() + timezone.timedelta(seconds=delay_seconds)
            delivery.save(update_fields=['status', 'error_message', 'next_retry_at', 'updated_at'])
            
            raise self.retry(exc=exc, countdown=delay_seconds)


def _process_webhook(delivery: EventDelivery):
    """Additional helper function to send HTTP POST request for webhook deliveries."""
    url = delivery.payload.get('url')
    if not url:
        raise ValueError("Webhook URL is missing in payload.")
    
    webhook_payload = {
        "event_uuid": str(delivery.event_uuid),
        "rule_id": delivery.rule_id,
        "device_serial": delivery.trigger_device_serial_id,
        "timestamp": timezone.now().isoformat()
    }
    
    response = requests.post(url, json=webhook_payload, timeout=10)
    
    delivery.response_status = response.status_code
    
    response.raise_for_status()


# def _process_notification(delivery: EventDelivery):
#     """Additional helper function to process notification deliveries."""
#     """NOTE: This is a placeholder. In a real implementation, this would interface with an email service, push notification service, etc."""

#     channel = delivery.payload.get('channel')
#     message = delivery.payload.get('message')
    
#     if not channel or not message:
#         raise ValueError("Notification channel or message missing in payload.")
    
#     # Here we just log the message for demonstration. In a real implementation, you would replace this with actual sending logic.

#     if channel == "email":
#         logger_celery.info("Pretending to send EMAIL: %s", message)
#     elif channel == "telegram":
#         logger_celery.info("Pretending to send TELEGRAM: %s", message)
#     else:
#         raise ValueError(f"Unsupported notification channel: {channel}")
    
#     delivery.response_status = 200

@shared_task
def _process_notification(delivery: EventDelivery):
    """Processes a notification delivery, sending an email if the channel is 'email'. Raises exceptions on failure to trigger retries."""
    
    channel = delivery.payload.get('channel')
    message_text = delivery.payload.get('message', 'Alert triggered.')
    recipient = delivery.payload.get('recipient')
    subject = delivery.payload.get('subject', f"IoT Alert: Rule {delivery.rule_id}")
    
    if not channel:
        raise ValueError("Notification channel missing in payload.")
    
    if channel == "email":
        if not recipient:
            raise ValueError("Recipient email is missing in payload.")
        
        full_message = (
            f"{message_text}\n\n"
            f"--- Alert Details ---\n"
            f"Device Serial: {delivery.trigger_device_serial_id}\n"
            f"Event UUID: {delivery.event_uuid}\n\n"
            f"Sent by IoT Hub Platform"
        )
        
        logger_celery.info(f"Sending real EMAIL to {recipient}...")
        
        send_mail(
            subject=subject,
            message=full_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@iot-hub.local'),
            recipient_list=[recipient],
            fail_silently=False, 
        )
    else:
        raise ValueError(f"Unsupported notification channel: {channel}")
    
    delivery.response_status = 200

@shared_task
def recover_stuck_deliveries():
    """Periodic task to find stuck deliveries and re-queue them in Celery."""

    now = timezone.now()

    pending_threshold = now - timedelta(minutes=5)
    
    processing_threshold = now - timedelta(minutes=15)

    stuck_deliveries = EventDelivery.objects.filter(
        Q(status=Status.PENDING, updated_at__lt=pending_threshold) |
        Q(status=Status.PROCESSING, updated_at__lt=processing_threshold) |
        Q(status=Status.RETRY, next_retry_at__lte=now)
    )

    count = 0
    for delivery in stuck_deliveries:
        delivery.updated_at = now
        delivery.save(update_fields=['updated_at'])
        
        logger_celery.warning(f"Recovering stuck delivery {delivery.id} (Status: {delivery.status})")
        
        process_delivery_task.delay(delivery.id)
        count += 1

    if count > 0:
        logger_celery.info(f"Recovered {count} stuck deliveries.")