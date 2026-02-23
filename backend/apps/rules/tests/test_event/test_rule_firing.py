"""
Tests verifying that rule firing:
  1. Creates an Event with correct field values
  2. Enqueues notify_event Celery task
  3. Enqueues deliver_webhook Celery task

Strategy: patch task .delay() so no broker is needed.
"""
import pytest
from unittest.mock import patch, call, MagicMock
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event
from apps.rules.services.action import Action
from apps.rules.services.rule_processor import RuleProcessor

pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user():
    return User.objects.create_user(
        username="fire_user", email="fire@example.com", password="pass123"
    )


@pytest.fixture
def device(user):
    return Device.objects.create(user=user, serial_id="FIRE-DEV-001", name="Fire Device")


@pytest.fixture
def metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric(device, metric):
    return DeviceMetric.objects.create(device=device, metric=metric)


@pytest.fixture
def rule(device_metric):
    return Rule.objects.create(
        name="Threshold Rule",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )


@pytest.fixture
def telemetry(device_metric):
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": 75},
    )


@pytest.fixture
def telemetry_below(device_metric):
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": 10},
    )


# ============================================================================
# Action.dispatch_action — Event creation
# ============================================================================


def test_dispatch_action_creates_event(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert event is not None
    assert Event.objects.filter(id=event.id).exists()


def test_dispatch_action_event_links_correct_rule(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert event.rule_id == rule.id


def test_dispatch_action_event_stores_trigger_telemetry_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert event.trigger_telemetry_id == telemetry.id


def test_dispatch_action_event_stores_trigger_device_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert event.trigger_device_id == telemetry.device_metric.device_id


def test_dispatch_action_event_timestamp_is_recent(rule, telemetry):
    before = timezone.now()
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)
    after = timezone.now()

    assert before <= event.timestamp <= after


def test_dispatch_action_event_acknowledged_defaults_false(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert event.acknowledged is False


def test_dispatch_action_persists_event_to_db(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    db_event = Event.objects.get(id=event.id)
    assert db_event.rule_id == rule.id
    assert db_event.trigger_telemetry_id == telemetry.id


# ============================================================================
# Action.dispatch_action — notify_event task enqueueing
# ============================================================================


def test_dispatch_action_enqueues_notify_event(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    mock_notify.assert_called_once_with(event.id)


def test_dispatch_action_enqueues_notify_event_with_correct_event_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    args, _ = mock_notify.call_args
    assert args[0] == event.id


# ============================================================================
# Action.dispatch_action — deliver_webhook task enqueueing
# ============================================================================


def test_dispatch_action_enqueues_deliver_webhook(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    mock_webhook.assert_called_once_with(event.id)


def test_dispatch_action_enqueues_deliver_webhook_with_correct_event_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    args, _ = mock_webhook.call_args
    assert args[0] == event.id


# ============================================================================
# Action.dispatch_action — both tasks enqueued together
# ============================================================================


def test_dispatch_action_enqueues_both_tasks(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert mock_notify.call_count == 1
    assert mock_webhook.call_count == 1


def test_dispatch_action_tasks_receive_same_event_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    notify_id = mock_notify.call_args[0][0]
    webhook_id = mock_webhook.call_args[0][0]
    assert notify_id == event.id
    assert webhook_id == event.id


# ============================================================================
# Action._enqueue — failure tolerance
# ============================================================================


def test_event_is_created_even_if_task_enqueue_fails(rule, telemetry):
    """
    _enqueue swallows all exceptions — Event must exist even when broker is down.
    """
    with patch("apps.rules.tasks.notify_event.delay", side_effect=Exception("broker down")), \
         patch("apps.rules.tasks.deliver_webhook.delay", side_effect=Exception("broker down")):
        event = Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert Event.objects.filter(id=event.id).exists()


def test_enqueue_failure_does_not_raise(rule, telemetry):
    """dispatch_action must not propagate task-level exceptions."""
    with patch("apps.rules.tasks.notify_event.delay", side_effect=RuntimeError("oops")), \
         patch("apps.rules.tasks.deliver_webhook.delay", side_effect=RuntimeError("oops")):
        try:
            Action.dispatch_action(rule=rule, telemetry=telemetry)
        except Exception:
            pytest.fail("dispatch_action must not raise when enqueueing fails")


def test_first_task_failure_does_not_prevent_second_task(rule, telemetry):
    """If notify_event.delay raises, deliver_webhook.delay must still be attempted."""
    with patch("apps.rules.tasks.notify_event.delay", side_effect=Exception("fail")), \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        Action.dispatch_action(rule=rule, telemetry=telemetry)

    mock_webhook.assert_called_once()


# ============================================================================
# RuleProcessor end-to-end: condition TRUE → Event + tasks
# ============================================================================


def test_rule_processor_fires_creates_event(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        RuleProcessor.run(telemetry)

    assert Event.objects.filter(rule=rule).count() == 1


def test_rule_processor_fires_enqueues_notify_event(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        RuleProcessor.run(telemetry)

    mock_notify.assert_called_once()


def test_rule_processor_fires_enqueues_deliver_webhook(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry)

    mock_webhook.assert_called_once()


def test_rule_processor_enqueues_tasks_with_created_event_id(rule, telemetry):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry)

    event = Event.objects.filter(rule=rule).first()
    assert event is not None
    mock_notify.assert_called_once_with(event.id)
    mock_webhook.assert_called_once_with(event.id)


# ============================================================================
# RuleProcessor: condition FALSE → no Event, no tasks
# ============================================================================


def test_rule_processor_no_event_when_condition_false(rule, telemetry_below):
    """Telemetry value 10 does NOT satisfy '>50' — no event, no tasks."""
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry_below)

    assert Event.objects.filter(rule=rule).count() == 0
    mock_notify.assert_not_called()
    mock_webhook.assert_not_called()


def test_rule_processor_no_tasks_when_condition_false(rule, telemetry_below):
    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry_below)

    assert mock_notify.call_count == 0
    assert mock_webhook.call_count == 0


# ============================================================================
# RuleProcessor: inactive rule → no Event, no tasks
# ============================================================================


def test_inactive_rule_does_not_fire_event(device_metric, telemetry):
    inactive = Rule.objects.create(
        name="Inactive",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=False,
    )

    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry)

    assert Event.objects.filter(rule=inactive).count() == 0
    mock_notify.assert_not_called()
    mock_webhook.assert_not_called()


# ============================================================================
# RuleProcessor: multiple rules → each gets its own Event + tasks
# ============================================================================


def test_multiple_rules_each_create_own_event(device_metric, telemetry):
    rule_a = Rule.objects.create(
        name="Rule A",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )
    rule_b = Rule.objects.create(
        name="Rule B",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 10},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    with patch("apps.rules.tasks.notify_event.delay"), \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        RuleProcessor.run(telemetry)

    assert Event.objects.filter(rule=rule_a).count() == 1
    assert Event.objects.filter(rule=rule_b).count() == 1


def test_multiple_rules_enqueue_tasks_per_rule(device_metric, telemetry):
    Rule.objects.create(
        name="Rule A",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )
    Rule.objects.create(
        name="Rule B",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 10},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(telemetry)

    assert mock_notify.call_count == 2
    assert mock_webhook.call_count == 2


def test_multiple_rules_tasks_called_with_distinct_event_ids(device_metric, telemetry):
    Rule.objects.create(
        name="Rule A",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )
    Rule.objects.create(
        name="Rule B",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 10},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        RuleProcessor.run(telemetry)

    called_event_ids = {c.args[0] for c in mock_notify.call_args_list}
    assert len(called_event_ids) == 2, "Each rule firing should produce a unique event_id"


def test_only_matching_rule_fires_when_mixed_conditions(device_metric, telemetry_below):
    """telemetry_below (value=10): '>50' fails, '>5' passes."""
    Rule.objects.create(
        name="High Threshold",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )
    low_rule = Rule.objects.create(
        name="Low Threshold",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 5},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay"):
        RuleProcessor.run(telemetry_below)

    assert Event.objects.filter(rule=low_rule).count() == 1
    assert mock_notify.call_count == 1


# ============================================================================
# Rate-condition rule → Event + tasks on trigger
# ============================================================================


def test_rate_rule_fires_creates_event_and_enqueues_tasks(device_metric):
    now = timezone.now()
    for v in [100, 105, 110]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rate_rule = Rule.objects.create(
        name="Rate Rule",
        device_metric=device_metric,
        condition={"type": "rate", "count": 3, "duration_minutes": 5},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    with patch("apps.rules.tasks.notify_event.delay") as mock_notify, \
         patch("apps.rules.tasks.deliver_webhook.delay") as mock_webhook:
        RuleProcessor.run(Telemetry.objects.filter(device_metric=device_metric).last())

    assert Event.objects.filter(rule=rate_rule).count() == 1
    mock_notify.assert_called_once()
    mock_webhook.assert_called_once()
