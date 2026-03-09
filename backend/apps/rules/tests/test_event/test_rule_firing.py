"""
Tests verifying that rule firing:
  1. Produces an event payload to Kafka via Action.dispatch_action
  2. RuleProcessor.run calls Action.dispatch_action for matching rules

Strategy: patch rule_event_producer so no broker is needed.
"""

import pytest
from unittest.mock import patch, MagicMock, ANY, call
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import caches

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event
from apps.rules.services.action import Action
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.utils.rule_engine_utils import PostgresTelemetryRepository
from apps.rules.utils.rule_engine_utils import TelemetryEvent

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
        action={"webhook": {"enabled": False}, "severity": "warning"},
        is_active=True,
    )


@pytest.fixture
def telemetry_orm(device_metric):
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": 75},
    )


@pytest.fixture
def telemetry(telemetry_orm):
    """Create TelemetryEvent (above threshold)."""
    return TelemetryEvent(
        device_serial_id=telemetry_orm.device_metric.device.serial_id,
        metric_type=telemetry_orm.device_metric.metric.metric_type,
        value=telemetry_orm.value_jsonb['v'],
        timestamp=telemetry_orm.ts,
    )


@pytest.fixture
def telemetry_below_orm(device_metric):
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": 10},
    )


@pytest.fixture
def telemetry_below(telemetry_below_orm):
    """Create TelemetryEvent (below threshold)."""
    return TelemetryEvent(
        device_serial_id=telemetry_below_orm.device_metric.device.serial_id,
        metric_type=telemetry_below_orm.device_metric.metric.metric_type,
        value=telemetry_below_orm.value_jsonb['v'],
        timestamp=telemetry_below_orm.ts,
    )


# ============================================================================
# Fixtures — Infrastructure
# ============================================================================


@pytest.fixture(autouse=True)
def force_postgres_repository():
    """Bypass Redis and always use PostgreSQL repository for rule engine."""
    with patch(
        "apps.rules.services.rule_processor.choose_repository",
        return_value=PostgresTelemetryRepository(),
    ):
        yield


@pytest.fixture(autouse=True)
def clear_rules_cache():
    """Override 'rules' cache with in-memory backend to avoid Redis connection."""
    from django.test.utils import override_settings

    with override_settings(
        CACHES={
            **{
                k: v
                for k, v in __import__(
                    'django.conf', fromlist=['settings']
                ).settings.CACHES.items()
                if k != 'rules'
            },
            "rules": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        }
    ):
        caches["rules"].clear()
        yield


@pytest.fixture
def mock_kafka_producer():
    """Patch the module-level rule_event_producer in action.py to avoid real Kafka."""
    mock_producer = MagicMock()
    with patch("apps.rules.services.action.rule_event_producer", mock_producer):
        yield mock_producer


# ============================================================================
# Action.dispatch_action — Kafka producer calls
# ============================================================================


def test_dispatch_action_calls_kafka_produce(rule, telemetry, mock_kafka_producer):
    """dispatch_action must call rule_event_producer.produce() exactly once."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    mock_kafka_producer.produce.assert_called_once()


def test_dispatch_action_calls_kafka_flush(rule, telemetry, mock_kafka_producer):
    """dispatch_action must call rule_event_producer.flush() to ensure delivery."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    mock_kafka_producer.flush.assert_called_once()


def test_dispatch_action_produces_with_rule_id_as_key(rule, telemetry, mock_kafka_producer):
    """Kafka message key should be the rule's primary key (as string)."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    assert kwargs["key"] == str(rule.id)


# ============================================================================
# Action.dispatch_action — Payload contents
# ============================================================================


def test_dispatch_action_payload_contains_event_uuid(rule, telemetry, mock_kafka_producer):
    """Produced payload must include a non-empty event_uuid."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    assert "event_uuid" in payload
    assert payload["event_uuid"]


def test_dispatch_action_payload_contains_rule_id(rule, telemetry, mock_kafka_producer):
    """Produced payload must contain the triggering rule's id."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    assert payload["rule_id"] == rule.id


def test_dispatch_action_payload_contains_device_serial_id(rule, telemetry, mock_kafka_producer):
    """Produced payload must contain the triggering device serial id."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    assert payload["trigger_device_serial_id"] == telemetry.device_serial_id


def test_dispatch_action_payload_contains_trigger_context(rule, telemetry, mock_kafka_producer):
    """Produced payload must include trigger_context with metric info."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    assert "trigger_context" in payload
    ctx = payload["trigger_context"]
    assert ctx["metric_type"] == telemetry.metric_type
    assert ctx["value"] == telemetry.value


def test_dispatch_action_payload_timestamp_is_recent(rule, telemetry, mock_kafka_producer):
    """rule_triggered_at in the payload should fall within the test window."""
    before = timezone.now()
    Action.dispatch_action(rule=rule, telemetry=telemetry)
    after = timezone.now()

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    triggered_at = datetime.fromisoformat(payload["rule_triggered_at"])
    assert before <= triggered_at <= after


def test_dispatch_action_payload_contains_action_from_rule(rule, telemetry, mock_kafka_producer):
    """Produced payload must carry the rule's action dict."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    payload = kwargs["payload"]
    assert payload["action"] == rule.action


def test_dispatch_action_does_not_create_event_in_db(rule, telemetry, mock_kafka_producer):
    """Action no longer writes Events to the DB directly — that is the consumer's job."""
    Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert Event.objects.count() == 0


# ============================================================================
# Action.dispatch_action — failure tolerance
# ============================================================================


def test_dispatch_action_does_not_raise_on_kafka_failure(rule, telemetry):
    """If Kafka produce raises, dispatch_action must swallow the error."""
    with patch(
        "apps.rules.services.action.rule_event_producer"
    ) as mock_producer:
        mock_producer.produce.side_effect = Exception("broker down")
        try:
            Action.dispatch_action(rule=rule, telemetry=telemetry)
        except Exception:
            pytest.fail("dispatch_action must not re-raise Kafka exceptions")


def test_dispatch_action_logs_exception_on_kafka_failure(rule, telemetry, caplog):
    """Kafka failures must be logged for observability."""
    import logging

    with patch(
        "apps.rules.services.action.rule_event_producer"
    ) as mock_producer:
        mock_producer.produce.side_effect = Exception("broker down")
        with caplog.at_level(logging.ERROR):
            Action.dispatch_action(rule=rule, telemetry=telemetry)

    assert any("Kafka" in r.message or "publish" in r.message for r in caplog.records)


# ============================================================================
# RuleProcessor end-to-end: condition TRUE → dispatch_action called
# ============================================================================


def test_rule_processor_fires_calls_dispatch_action(rule, telemetry):
    """When condition is met, RuleProcessor.run must call Action.dispatch_action."""
    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(telemetry)

    mock_dispatch.assert_called_once_with(rule, ANY)


def test_rule_processor_fires_produces_to_kafka(rule, telemetry, mock_kafka_producer):
    """RuleProcessor end-to-end: matching rule → Kafka produce is called."""
    RuleProcessor.run(telemetry)

    mock_kafka_producer.produce.assert_called_once()


def test_rule_processor_payload_has_correct_rule_id(rule, telemetry, mock_kafka_producer):
    """Kafka payload produced during RuleProcessor run must reference the triggered rule."""
    RuleProcessor.run(telemetry)

    _, kwargs = mock_kafka_producer.produce.call_args
    assert kwargs["payload"]["rule_id"] == rule.id


# ============================================================================
# RuleProcessor: condition FALSE → no dispatch
# ============================================================================


def test_rule_processor_no_dispatch_when_condition_false(rule, telemetry_below):
    """Value 10 does NOT satisfy '>50' — dispatch_action must not be called."""
    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(telemetry_below)

    mock_dispatch.assert_not_called()


def test_rule_processor_no_kafka_produce_when_condition_false(rule, telemetry_below, mock_kafka_producer):
    """No Kafka message when the threshold condition is not met."""
    RuleProcessor.run(telemetry_below)

    mock_kafka_producer.produce.assert_not_called()


# ============================================================================
# RuleProcessor: inactive rule → no dispatch
# ============================================================================


def test_inactive_rule_does_not_dispatch(device_metric, telemetry):
    """Inactive rule must not trigger dispatch_action even if condition would match."""
    Rule.objects.create(
        name="Inactive",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action={"webhook": {"enabled": False}},
        is_active=False,
    )

    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(telemetry)

    mock_dispatch.assert_not_called()


# ============================================================================
# RuleProcessor: multiple rules → each triggers its own dispatch
# ============================================================================


def test_multiple_rules_each_call_dispatch_action(device_metric, telemetry):
    """Two matching rules should each independently call dispatch_action."""
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

    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(telemetry)

    assert mock_dispatch.call_count == 2
    called_rules = {c.args[0] for c in mock_dispatch.call_args_list}
    assert rule_a in called_rules
    assert rule_b in called_rules


def test_multiple_rules_produce_distinct_event_uuids(device_metric, telemetry, mock_kafka_producer):
    """Each rule firing must generate a unique event_uuid in the Kafka payload."""
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

    RuleProcessor.run(telemetry)

    assert mock_kafka_producer.produce.call_count == 2
    uuids = {c[1]["payload"]["event_uuid"] for c in mock_kafka_producer.produce.call_args_list}
    assert len(uuids) == 2, "Each rule firing must produce a unique event_uuid"


def test_only_matching_rule_dispatches_when_mixed_conditions(device_metric, telemetry_below):
    """telemetry_below (value=10): '>50' fails, '>5' passes — only low rule dispatches."""
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

    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(telemetry_below)

    assert mock_dispatch.call_count == 1
    assert mock_dispatch.call_args.args[0] == low_rule


# ============================================================================
# Rate-condition rule → dispatch on trigger
# ============================================================================


def test_rate_rule_fires_calls_dispatch_action(device_metric):
    """Rate rule with count=3 met → dispatch_action must be called once."""
    now = timezone.now()
    for i, v in enumerate([100, 105, 110]):
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            ts=now - timedelta(minutes=1) + timedelta(seconds=i),
        )

    rate_rule = Rule.objects.create(
        name="Rate Rule",
        device_metric=device_metric,
        condition={"type": "rate", "count": 3, "duration_minutes": 5},
        action={"webhook": {"enabled": False}},
        is_active=True,
    )

    latest = Telemetry.objects.filter(device_metric=device_metric).last()

    with patch.object(Action, "dispatch_action") as mock_dispatch:
        RuleProcessor.run(latest)

    mock_dispatch.assert_called_once_with(rate_rule, ANY)
