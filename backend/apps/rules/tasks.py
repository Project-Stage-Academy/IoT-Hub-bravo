from celery import shared_task
from celery.utils.log import get_task_logger

from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor
from django.conf import settings
import requests
from requests.exceptions import RequestException
from apps.rules.models.event import Event

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


@shared_task(
    name="notify_event",
)
def notify_event(event_id: int):
    """
    Simple notification task: logs the event firing. Could be extended to persist
    notifications or push to a user-notification service.
    """
    try:
        event = Event.objects.select_related('rule').get(id=event_id)
    except Event.DoesNotExist:
        logger_celery.warning("notify_event: Event not found", extra={"event_id": event_id})
        return

    payload = {
        "event_id": event.id,
        "rule_id": event.rule.id,
        "rule_name": event.rule.name,
        "trigger_telemetry_id": event.trigger_telemetry_id,
        "trigger_device_id": event.trigger_device_id,
        "timestamp": event.timestamp.isoformat(),
    }

    logger_celery.info("Event notification enqueued", extra={"notification": payload})


@shared_task(
    bind=True,
    name="deliver_webhook",
    autoretry_for=(RequestException,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def deliver_webhook(self, event_id: int):
    """
    Deliver a webhook for the given event. Will retry on network errors.

    Safe default: will NOT perform external HTTP calls unless
    `settings.RULES_ALLOW_WEBHOOKS` is True.
    """
    try:
        event = Event.objects.select_related('rule').get(id=event_id)
    except Event.DoesNotExist:
        logger_celery.warning("deliver_webhook: Event not found", extra={"event_id": event_id})
        return

    if not getattr(settings, 'RULES_ALLOW_WEBHOOKS', False):
        logger_celery.info("Webhook delivery disabled by settings", extra={"event_id": event_id})
        return

    actions = event.rule.action or {}
    webhook_cfg = actions.get("webhook") or {}

    if not webhook_cfg.get("enabled"):
        logger_celery.info("Webhook disabled for rule", extra={"rule_id": event.rule_id})
        return

    resolved_url = webhook_cfg.get("url")
    if not resolved_url:
        logger_celery.warning("Webhook enabled but url missing", extra={"rule_id": event.rule_id})
        return

    body = {
        "event_id": event.id,
        "rule_id": event.rule.id,
        "rule_name": event.rule.name,
        "trigger_telemetry_id": event.trigger_telemetry_id,
        "trigger_device_id": event.trigger_device_id,
        "timestamp": event.timestamp.isoformat(),
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(resolved_url, json=body, headers=headers, timeout=10)
        if not (200 <= resp.status_code < 300):
            logger_celery.warning(
                "Webhook delivery failed (status)",
                extra={"status": resp.status_code, "url": resolved_url, "event_id": event.id},
            )
            raise RequestException(f"Non-2xx response: {resp.status_code}")

        logger_celery.info("Webhook delivered", extra={"url": resolved_url, "event_id": event.id})
    except RequestException as exc:
        logger_celery.warning(
            "Webhook delivery error, will retry", extra={"error": str(exc), "event_id": event.id}
        )
        raise
