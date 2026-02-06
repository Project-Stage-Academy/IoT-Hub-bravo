import pytest
from unittest.mock import patch

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.services.condition_evaluator import ConditionEvaluator


@pytest.mark.django_db
def test_rule_processor_creates_event_real():
    # Setup
    user = User.objects.create(username="test", email="a@b.com", password="123")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)
    
    # Create telemetry with value_numeric instead of value_jsonb
    telemetry = Telemetry.objects.create(
        device_metric=device_metric, 
        value_jsonb = {"t": "numeric", "v": 111}
    )
    
    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"metric": "temperature", "operator": ">", "value": 100},
        action="notify",
        is_active=True
    )

    processor = RuleProcessor()

    # Mock the condition evaluator to always return True
    with patch.object(ConditionEvaluator, "evaluate_condition", return_value = True):
        processor.run(telemetry)

    # Verify event was created
    events = Event.objects.filter(rule=rule)
    assert events.count() == 1
    assert events.first().rule == rule


@pytest.mark.django_db
def test_rule_processor_creates_event_when_condition_true():
    """Event should be created when condition is TRUE"""
    user = User.objects.create(username="test", email="a@b.com")
    device = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)
    
    # 111 > 100 = TRUE
    telemetry = Telemetry.objects.create(
        device_metric=device_metric, 
        value_jsonb = {"t": "numeric", "v": 111}
    )
    
    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"metric": "temperature", "operator": ">", "value": 100},
        action="notify",
        is_active=True
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    events = Event.objects.filter(rule=rule)
    assert events.count() == 1, "Event should be created when 111 > 100"


@pytest.mark.django_db
def test_rule_processor_no_event_when_condition_false():
    """Event should NOT be created when condition is FALSE"""
    user = User.objects.create(username="test2", email="b@b.com")
    device = Device.objects.create(user=user, serial_id="dev2", name="Device 2")
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric = DeviceMetric.objects.create(device=device, metric=metric)
    
    # 99 > 100 = FALSE
    telemetry = Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb = {"t": "numeric", "v": 90}
    )
    
    rule = Rule.objects.create(
        device_metric=device_metric,
        condition={"metric": "temperature", "operator": ">", "value": 100},
        action="notify",
        is_active=True
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    events = Event.objects.filter(rule=rule)
    assert events.count() == 0, "Event should NOT be created when 99 > 100"


@pytest.mark.django_db
def test_rule_processor_only_processes_matching_device_metric():
    """Test that rules only process telemetry from their device_metric"""
    user = User.objects.create(username="test", email="a@b.com", password="123")
    device1 = Device.objects.create(user=user, serial_id="dev1", name="Device 1")
    
    metric = Metric.objects.create(metric_type="temperature", data_type="numeric")
    device_metric1 = DeviceMetric.objects.create(device=device1, metric=metric)
    
    telemetry = Telemetry.objects.create(
        device_metric=device_metric1,
        value_jsonb = {"t": "numeric", "v": 111}
    )
    
    # Rule for different cond metric
    rule = Rule.objects.create(
        device_metric=device_metric1,
        condition={"metric": "humidity", "operator": ">", "value": 100},
        action="notify",
        is_active=True
    )

    processor = RuleProcessor()
    processor.run(telemetry)

    # No event should be created (different metrics)
    assert Event.objects.filter(rule=rule).count() == 0

