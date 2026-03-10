"""Integration test: Device → Telemetry → Rule Processor → Kafka → Event"""

import pytest
from celery import current_app
from unittest.mock import patch, MagicMock

from apps.devices.models import Telemetry
from apps.rules.models import Event
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.utils.rule_engine_utils import PostgresTelemetryRepository
from apps.rules.consumers.event_db_handler import EventDBHandler
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
    RuleFactory,
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def force_postgres_repository():
    """Bypass Redis and always use PostgreSQL repository for rule engine."""
    with patch(
        "apps.rules.services.rule_processor.choose_repository",
        return_value=PostgresTelemetryRepository(),
    ):
        yield


@pytest.fixture(autouse=True)
def use_locmem_rules_cache(settings):
    """Replace Redis-backed 'rules' cache with in-memory cache."""
    settings.CACHES = {
        **{k: v for k, v in settings.CACHES.items() if k != "rules"},
        "rules": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }


class TestRuleProcessorCeleryIntegration:
    """Integration tests for Rule Processor with Celery."""

    @pytest.fixture(autouse=True)
    def celery_eager_mode(self, settings):
        """Run Celery tasks synchronously in tests."""
        settings.CELERY_TASK_ALWAYS_EAGER = True
        current_app.conf.task_always_eager = True

    def test_e2e_telemetry_triggers_rule_creates_event(self):
        """
        E2E: Telemetry → RuleProcessor → Action.dispatch_action → Kafka payload
             → EventDBHandler → Event saved to DB.

        The Kafka broker is replaced by capturing the produced payload and
        feeding it directly into the EventDBHandler, so no real broker is needed.
        """
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

        # Intercept Kafka produce to capture the payload
        produced_payloads = []
        mock_producer = MagicMock()
        mock_producer.produce.side_effect = lambda payload, key=None: produced_payloads.append(
            payload
        )

        with patch("apps.rules.services.action.rule_event_producer", mock_producer):
            RuleProcessor.run(telemetry)

        # Verify that a payload was produced to Kafka
        assert len(produced_payloads) == 1
        payload = produced_payloads[0]
        assert payload["rule_id"] == rule.id
        assert payload["trigger_device_serial_id"] == device.serial_id

        # Simulate the Kafka consumer processing the payload → creates Event in DB
        EventDBHandler().handle(payload)

        # Assert Event was created
        events = Event.objects.filter(rule=rule)
        assert events.count() == 1
        assert events.first().trigger_device_serial_id == device.serial_id

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
