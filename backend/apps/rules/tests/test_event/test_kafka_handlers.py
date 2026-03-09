"""
Tests for Kafka consumer handlers:
  - EventDBHandler  (saves Event to DB)
  - EventNotificationHandler  (creates EventDelivery + dispatches Celery via on_commit)
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from django.db import DatabaseError, transaction

from apps.rules.consumers.event_db_handler import EventDBHandler
from apps.rules.consumers.event_notification_handler import EventNotificationHandler
from apps.rules.models.event import Event
from apps.rules.models.event_delivery import EventDelivery, DeliveryType, Status
from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric
from apps.rules.models import Rule

pytestmark = pytest.mark.django_db


# ============================================================================
# Shared fixtures
# ============================================================================


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="handler_user", email="handler@example.com", password="pass123"
    )


@pytest.fixture
def device(user):
    return Device.objects.create(user=user, serial_id="HANDLER-DEV-001", name="Handler Device")


@pytest.fixture
def metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric(device, metric):
    return DeviceMetric.objects.create(device=device, metric=metric)


@pytest.fixture
def rule(device_metric):
    return Rule.objects.create(
        name="Handler Rule",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"severity": "warning"},
        is_active=True,
    )


@pytest.fixture
def valid_db_payload(rule):
    """Minimal valid payload for EventDBHandler."""
    return {
        "event_uuid": str(uuid.uuid4()),
        "rule_triggered_at": "2024-01-01T10:00:00+00:00",
        "rule_id": rule.id,
        "trigger_device_serial_id": "HANDLER-DEV-001",
        "trigger_context": {"metric_type": "temperature", "value": 75.0},
    }


@pytest.fixture
def webhook_only_payload():
    return {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "NOTIF-DEV-001",
        "action": {
            "webhook": {"enabled": True, "url": "https://example.com/hook"},
        },
    }


@pytest.fixture
def notification_only_payload():
    return {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "NOTIF-DEV-001",
        "action": {
            "notification": {
                "enabled": True,
                "channel": "email",
                "recipient": "user@example.com",
            },
        },
    }


@pytest.fixture
def both_channels_payload():
    return {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "NOTIF-DEV-001",
        "action": {
            "webhook": {"enabled": True, "url": "https://example.com/hook"},
            "notification": {
                "enabled": True,
                "channel": "email",
                "recipient": "user@example.com",
                "subject": "Alert",
                "message": "Threshold exceeded",
            },
        },
    }


# ============================================================================
# EventDBHandler — happy path
# ============================================================================


def test_event_db_handler_creates_event_from_valid_payload(valid_db_payload):
    """Handler should persist a new Event row using data from the payload."""
    handler = EventDBHandler()
    handler.handle(valid_db_payload)

    assert Event.objects.filter(event_uuid=valid_db_payload["event_uuid"]).exists()


def test_event_db_handler_sets_correct_fields(valid_db_payload):
    """Created Event should have its FK fields correctly populated."""
    handler = EventDBHandler()
    handler.handle(valid_db_payload)

    event = Event.objects.get(event_uuid=valid_db_payload["event_uuid"])
    assert event.rule_id == valid_db_payload["rule_id"]
    assert event.trigger_device_serial_id == valid_db_payload["trigger_device_serial_id"]
    assert event.trigger_context == valid_db_payload["trigger_context"]
    assert event.acknowledged is False


def test_event_db_handler_handles_list_payload(valid_db_payload, rule):
    """
    handle() must also accept a list of payloads and process each one,
    because Kafka may batch messages.
    """
    payload2 = {**valid_db_payload, "event_uuid": str(uuid.uuid4())}
    handler = EventDBHandler()
    handler.handle([valid_db_payload, payload2])

    assert Event.objects.count() == 2


def test_event_db_handler_is_idempotent_for_duplicate_uuid(valid_db_payload):
    """
    If the same event_uuid arrives twice (Kafka at-least-once delivery),
    the handler should silently skip the second message without creating a duplicate.
    """
    handler = EventDBHandler()
    handler.handle(valid_db_payload)
    handler.handle(valid_db_payload)  

    assert Event.objects.filter(event_uuid=valid_db_payload["event_uuid"]).count() == 1


# ============================================================================
# EventDBHandler — Poison Pill protection (negative paths)
# ============================================================================


def test_event_db_handler_swallows_missing_key(db):
    """
    Poison Pill: payload missing required keys should be silently dropped
    (logged but NOT re-raised), preventing the consumer from crashing.
    """
    handler = EventDBHandler()
    handler.handle({"rule_id": 1})
    assert Event.objects.count() == 0


def test_event_db_handler_swallows_value_error(db):
    """
    Poison Pill: patching get_or_create to raise ValueError simulates bad data.
    The handler must absorb it and NOT propagate.
    """
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_triggered_at": "2024-01-01T10:00:00+00:00",
        "rule_id": 1,
        "trigger_device_serial_id": "DEV",
    }
    handler = EventDBHandler()

    with patch.object(Event.objects, 'get_or_create', side_effect=ValueError("bad value")):
        handler.handle(payload)  

    assert Event.objects.count() == 0


def test_event_db_handler_raises_on_database_error(db):
    """
    DatabaseError is NOT a Poison Pill — it indicates infrastructure failure
    and must be re-raised so the consumer can handle it (crash-loop / alerting).
    """
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_triggered_at": "2024-01-01T10:00:00+00:00",
        "rule_id": 999,
        "trigger_device_serial_id": "DEV",
    }
    handler = EventDBHandler()

    with patch.object(Event.objects, 'get_or_create', side_effect=DatabaseError("db down")):
        with pytest.raises(DatabaseError):
            handler.handle(payload)


def test_event_db_handler_logs_missing_key(db, caplog):
    """Verify the KeyError branch writes an ERROR log for observability."""
    import logging

    handler = EventDBHandler()

    with caplog.at_level(logging.ERROR):
        handler.handle({"wrong_key": "value"})

    assert any("Missing required field" in record.message for record in caplog.records)


# ============================================================================
# EventNotificationHandler — happy path
# ============================================================================


def test_notification_handler_creates_webhook_delivery(webhook_only_payload):
    """Handler should persist an EventDelivery of type WEBHOOK."""
    with patch('apps.rules.consumers.event_notification_handler.process_delivery_task'):
        EventNotificationHandler().handle(webhook_only_payload)

    assert EventDelivery.objects.filter(
        event_uuid=webhook_only_payload["event_uuid"],
        delivery_type=DeliveryType.WEBHOOK,
    ).exists()


def test_notification_handler_creates_notification_delivery(notification_only_payload):
    """Handler should persist an EventDelivery of type NOTIFICATION."""
    with patch('apps.rules.consumers.event_notification_handler.process_delivery_task'):
        EventNotificationHandler().handle(notification_only_payload)

    assert EventDelivery.objects.filter(
        event_uuid=notification_only_payload["event_uuid"],
        delivery_type=DeliveryType.NOTIFICATION,
    ).exists()


def test_notification_handler_creates_both_deliveries(both_channels_payload):
    """When both webhook and notification are enabled, two EventDelivery rows are created."""
    with patch('apps.rules.consumers.event_notification_handler.process_delivery_task'):
        EventNotificationHandler().handle(both_channels_payload)

    assert EventDelivery.objects.filter(
        event_uuid=both_channels_payload["event_uuid"]
    ).count() == 2


def test_notification_handler_delivery_status_defaults_to_pending(webhook_only_payload):
    """Newly created deliveries should start in PENDING state."""
    with patch('apps.rules.consumers.event_notification_handler.process_delivery_task'):
        EventNotificationHandler().handle(webhook_only_payload)

    delivery = EventDelivery.objects.get(event_uuid=webhook_only_payload["event_uuid"])
    assert delivery.status == Status.PENDING


def test_notification_handler_skips_when_action_is_empty(db):
    """If 'action' is empty, nothing should be created."""
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "DEV",
        "action": {},
    }
    EventNotificationHandler().handle(payload)
    assert EventDelivery.objects.count() == 0


def test_notification_handler_skips_disabled_webhook(db):
    """webhook.enabled=False should not create a delivery row."""
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "DEV",
        "action": {"webhook": {"enabled": False, "url": "https://example.com"}},
    }
    EventNotificationHandler().handle(payload)
    assert EventDelivery.objects.count() == 0


def test_notification_handler_is_idempotent(webhook_only_payload):
    """
    If handle() is called twice with the same payload (Kafka at-least-once),
    get_or_create prevents duplicate rows.
    """
    with patch('apps.rules.consumers.event_notification_handler.process_delivery_task'):
        handler = EventNotificationHandler()
        handler.handle(webhook_only_payload)
        handler.handle(webhook_only_payload)  

    assert EventDelivery.objects.filter(
        event_uuid=webhook_only_payload["event_uuid"]
    ).count() == 1


# ============================================================================
# EventNotificationHandler — atomic transaction / rollback
# ============================================================================


@pytest.mark.django_db(transaction=True)
def test_notification_handler_atomic_rollback_on_second_create_failure():
    """
    Both _create_and_dispatch calls live inside a single transaction.atomic() block.
    If the SECOND call raises a DatabaseError, the FIRST delivery must also be
    rolled back (atomicity guarantee from Outbox/transactional-inbox pattern).
    """
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "DEV",
        "action": {
            "webhook": {"enabled": True, "url": "https://example.com"},
            "notification": {"enabled": True, "channel": "email", "recipient": "a@b.com"},
        },
    }

    handler = EventNotificationHandler()
    original_get_or_create = EventDelivery.objects.get_or_create
    call_count = [0]

    def fail_on_second(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] >= 2:
            raise DatabaseError("Forced DB failure on second call")
        return original_get_or_create(*args, **kwargs)

    with patch.object(EventDelivery.objects, 'get_or_create', side_effect=fail_on_second):
        with pytest.raises(DatabaseError):
            handler.handle(payload)

    assert EventDelivery.objects.count() == 0


# ============================================================================
# EventNotificationHandler — transaction.on_commit fires Celery task
# ============================================================================


@pytest.mark.django_db(transaction=True)
def test_notification_handler_on_commit_dispatches_celery_task(webhook_only_payload):
    """
    process_delivery_task.delay() is wrapped in transaction.on_commit() so it
    only fires AFTER the transaction commits.  Using transaction=True ensures
    a real commit happens so the callback actually runs.
    """
    with patch(
        'apps.rules.consumers.event_notification_handler.process_delivery_task'
    ) as mock_task:
        EventNotificationHandler().handle(webhook_only_payload)

    mock_task.delay.assert_called_once()
    delivery_id = mock_task.delay.call_args[0][0]
    assert EventDelivery.objects.filter(id=delivery_id).exists()


@pytest.mark.django_db(transaction=True)
def test_notification_handler_on_commit_dispatches_two_tasks_for_both_channels(
    both_channels_payload,
):
    """When both webhook and notification are created, two .delay() calls are dispatched."""
    with patch(
        'apps.rules.consumers.event_notification_handler.process_delivery_task'
    ) as mock_task:
        EventNotificationHandler().handle(both_channels_payload)

    assert mock_task.delay.call_count == 2


# ============================================================================
# EventNotificationHandler — Poison Pill protection
# ============================================================================


def test_notification_handler_swallows_missing_key(db):
    """Missing required keys are logged and dropped, not re-raised."""
    EventNotificationHandler().handle({"wrong": "data"})
    assert EventDelivery.objects.count() == 0


def test_notification_handler_raises_on_database_error(db):
    """DatabaseError bypasses the Poison Pill guard and is re-raised."""
    payload = {
        "event_uuid": str(uuid.uuid4()),
        "rule_id": 1,
        "trigger_device_serial_id": "DEV",
        "action": {"webhook": {"enabled": True, "url": "https://example.com"}},
    }

    with patch.object(
        EventDelivery.objects, 'get_or_create', side_effect=DatabaseError("db down")
    ):
        with pytest.raises(DatabaseError):
            EventNotificationHandler().handle(payload)
