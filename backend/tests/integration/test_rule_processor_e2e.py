"""Integration test: Device → Telemetry → Rule Processor → Event"""

import pytest
from celery import current_app

from apps.devices.models import Telemetry
from apps.rules.models import Event
from apps.rules.services.rule_processor import RuleProcessor
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
    RuleFactory,
)


pytestmark = pytest.mark.django_db


class TestRuleProcessorCeleryIntegration:
    """Integration tests for Rule Processor with Celery."""

    @pytest.fixture(autouse=True)
    def celery_eager_mode(self, settings):
        """Run Celery tasks synchronously in tests."""
        settings.CELERY_TASK_ALWAYS_EAGER = True
        current_app.conf.task_always_eager = True

    def test_e2e_telemetry_triggers_rule_creates_event(self):
        """E2E: Telemetry → Rule Processor Task → Event created."""
        # Setup
        device = DeviceFactory(serial_id="E2E-001")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        device_metric = DeviceMetricFactory(device=device, metric=metric)

        rule = RuleFactory(
            device_metric=device_metric,
            condition={"type": "threshold", "operator": ">", "value": 30},
            is_active=True,
        )

        # Create telemetry that triggers rule (35 > 30)
        telemetry = Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": 35},
        )

        # Run Rule Processor
        RuleProcessor.run(telemetry)

        # Assert Event was created
        events = Event.objects.filter(rule=rule)
        assert events.count() == 1
        assert events.first().trigger_telemetry_id == telemetry.id

    def test_e2e_telemetry_below_threshold_no_event(self):
        """E2E: Telemetry below threshold → No Event created."""
        device = DeviceFactory(serial_id="E2E-002")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        device_metric = DeviceMetricFactory(device=device, metric=metric)

        rule = RuleFactory(
            device_metric=device_metric,
            condition={"type": "threshold", "operator": ">", "value": 30},
            is_active=True,
        )

        # Create telemetry that does NOT trigger rule (25 < 30)
        telemetry = Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": 25},
        )

        # Run Rule Processor
        RuleProcessor.run(telemetry)

        # Assert NO Event was created
        events = Event.objects.filter(rule=rule)
        assert events.count() == 0

    def test_e2e_inactive_rule_no_event(self):
        """E2E: Inactive rule → No Event created even if condition matches."""
        device = DeviceFactory(serial_id="E2E-003")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        device_metric = DeviceMetricFactory(device=device, metric=metric)

        rule = RuleFactory(
            device_metric=device_metric,
            condition={"type": "threshold", "operator": ">", "value": 30},
            is_active=False,  # Inactive!
        )

        telemetry = Telemetry.objects.create(
            device_metric=device_metric,
            value_jsonb={"t": "numeric", "v": 35},
        )

        RuleProcessor.run(telemetry)

        events = Event.objects.filter(rule=rule)
        assert events.count() == 0
