import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.services.condition_evaluator import ConditionEvaluator


@pytest.mark.django_db
def test_rule_processor_creates_event_real():
    """Create event"""
    user = User.objects.create(username="test", email="a@b.com", password="123")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    # Create telemetry with value_numeric instead of value_jsonb
    telemetry = Telemetry.objects.create(
        device_metric=device_metric, value_jsonb={"t": "numeric", "v": 111}
    )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 100},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()

    # Mock the condition evaluator to always return True
    with patch.object(ConditionEvaluator, "evaluate_condition", return_value=True):
        processor.run(telemetry)

    # Verify event was created
    events = Event.objects.filter(rule=rule)
    assert events.count() == 1
    assert events.first().rule == rule


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_threshold_type_true():
    """Event should be created when condition is TRUE"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    # 111 > 100 = TRUE
    telemetry = Telemetry.objects.create(
        device_metric=device_metric, value_jsonb={"t": "numeric", "v": 111}
    )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 100},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    events = Event.objects.filter(rule=rule)
    assert events.count() == 1, "Event should be created when 111 > 100"


@pytest.mark.django_db
def test_rule_processor_no_event_when_condition_threshold_type_false():
    """Event should NOT be created when condition is FALSE"""
    user = User.objects.create(username="test2", email="b@b.com")
    device = Device.objects.create(user=user, serial_id="dev2", name="Device 2")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    # 99 > 100 = FALSE
    telemetry = Telemetry.objects.create(
        device_metric=device_metric, value_jsonb={"t": "numeric", "v": 90}
    )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 100},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    events = Event.objects.filter(rule=rule)
    assert events.count() == 0, "Event should NOT be created when 99 > 100"


@pytest.mark.django_db
def test_rule_processor_only_processes_matching_device_metric_threshold_type():
    """Test that rules only process telemetry from their device_metric"""
    user = User.objects.create(username="test", email="a@b.com", password="123")
    device1 = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    device2 = Device.objects.create(user=user, serial_id="dev2", name="Device 2")

    metric1 = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric1 = DeviceMetric.objects.create(device=device1, metric=metric1)

    metric2 = Metric.objects.create(metric_type="humidity", data_type="numeric")
    device_metric2 = DeviceMetric.objects.create(device=device2, metric=metric2)

    telemetry = Telemetry.objects.create(
        device_metric=device_metric1, value_jsonb={"t": "numeric", "v": 111}
    )

    # Rule for different cond metric
    rule = Rule.objects.create(
        device_metric=device_metric2,
        condition={"type": "threshold", "operator": ">", "value": 100},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    # No event should be created (different metrics)
    assert Event.objects.filter(rule=rule).count() == 0


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_rate_type_true():
    """Event should be created when rate condition is met"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    # create test data for telemetry
    now = timezone.now()
    for v in [100, 105, 110]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"type": "rate", "count": 3, "duration_minutes": 5},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(Telemetry.objects.last())

    events = Event.objects.filter(rule=rule)
    assert events.count() == 1, "Event should be created when rate condition is met"


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_rate_type_false():
    """Event should NOT be created when rate condition is NOT met"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    now = timezone.now()
    # create 2 telemetry for the last 5 min (less then count=3)
    for v in [100, 105]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"type": "rate", "count": 3, "duration_minutes": 5},
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(Telemetry.objects.last())

    events = Event.objects.filter(rule=rule)
    assert events.count() == 0, "Event should NOT be created when rate condition is not met"


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_composite_and_true():
    """Event should be created when composite AND condition is met"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    now = timezone.now()

    # Telemetry for rate (3 events within 5 min) and threshold
    for v in [100, 95, 99]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={
            "type": "composite",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 90},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(Telemetry.objects.last())

    events = Event.objects.filter(rule=rule)
    assert events.count() == 1, "Event should be created when composite AND condition is met"


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_composite_or_true():
    """Event should be created when composite OR condition is met"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    now = timezone.now()
    # Telemetry for threshold (fails)
    Telemetry.objects.create(
        device_metric=device_metric, value_jsonb={"t": "numeric", "v": 100}, created_at=now
    )

    # Telemetry for rate (3 events within 5 min, meets condition)
    for v in [100, 111, 110]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={
            "type": "composite",
            "operator": "OR",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 110},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(Telemetry.objects.last())

    events = Event.objects.filter(rule=rule)
    assert events.count() == 1, "Event should be created when composite OR condition is met"


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_composite_false():
    """Event should NOT be created when composite AND condition fails"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)

    now = timezone.now()

    # Telemetry for rate (only 2 events, less than count=3)
    for v in [111, 115]:
        Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": v},
            created_at=now - timedelta(minutes=1),
        )

    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={
            "type": "composite",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 110},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
        action="notify",
        is_active=True,
    )

    processor = RuleProcessor()
    processor.run(Telemetry.objects.last())

    events = Event.objects.filter(rule=rule)
    assert events.count() == 0, "Event should NOT be created when composite AND condition fails"
