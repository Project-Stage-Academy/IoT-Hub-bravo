"""
Integration tests: MQTT/Kafka payload → Celery task → Validate → Create → DB.

Tests call ingest_telemetry_payload directly with real DB to verify
the full ingestion pipeline end-to-end.
"""

import sys

sys.path.insert(0, '/app')

import pytest
from unittest.mock import patch

from apps.devices.models.telemetry import Telemetry
from apps.devices.tasks import ingest_telemetry_payload
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
)

pytestmark = pytest.mark.django_db


def make_payload(device_serial, metrics, ts='2026-02-04T12:00:00Z'):
    """Build a valid telemetry payload dict."""
    return {
        'schema_version': 1,
        'device': device_serial,
        'metrics': metrics,
        'ts': ts,
    }


@pytest.fixture
def setup_device_with_metrics():
    """Create a device with temperature (numeric) and door_open (bool) metrics."""
    device = DeviceFactory(serial_id='INT-001', is_active=True)
    temp_metric = MetricFactory(metric_type='temperature', data_type='numeric', unit='celsius')
    door_metric = MetricFactory(metric_type='door_open', data_type='bool', unit='open')
    dm_temp = DeviceMetricFactory(device=device, metric=temp_metric)
    dm_door = DeviceMetricFactory(device=device, metric=door_metric)
    return device, dm_temp, dm_door


# ──────────────────────────────────────────────
#  Single payload
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
class TestSinglePayload:
    """E2E tests for single dict payloads."""

    def test_valid_single_payload_creates_telemetry(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Valid single payload creates Telemetry rows in DB."""
        device, dm_temp, dm_door = setup_device_with_metrics

        payload = make_payload(
            'INT-001',
            {
                'temperature': {'value': 22.5, 'unit': 'celsius'},
                'door_open': {'value': True, 'unit': 'open'},
            },
        )

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.filter(device_metric=dm_temp).count() == 1
        assert Telemetry.objects.filter(device_metric=dm_door).count() == 1

        temp_row = Telemetry.objects.get(device_metric=dm_temp)
        assert temp_row.value_jsonb == {'t': 'numeric', 'v': 22.5}

    def test_unknown_device_creates_no_telemetry(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Payload for non-existent device creates no Telemetry."""
        payload = make_payload(
            'UNKNOWN-999',
            {
                'temperature': {'value': 22.5, 'unit': 'celsius'},
            },
        )

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.count() == 0

    def test_inactive_device_creates_no_telemetry(
        self,
        mock_publish,
    ):
        """Payload for inactive device creates no Telemetry."""
        device = DeviceFactory(serial_id='INACTIVE-001', is_active=False)
        metric = MetricFactory(metric_type='temperature', data_type='numeric', unit='celsius')
        DeviceMetricFactory(device=device, metric=metric)

        payload = make_payload(
            'INACTIVE-001',
            {
                'temperature': {'value': 22.5, 'unit': 'celsius'},
            },
        )

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.count() == 0


# ──────────────────────────────────────────────
#  Batch payloads
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
class TestBatchPayload:
    """E2E tests for batch (list) payloads."""

    def test_valid_batch_creates_all_telemetry(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Batch of valid payloads creates all Telemetry rows."""
        device, dm_temp, dm_door = setup_device_with_metrics

        payloads = [
            make_payload(
                'INT-001',
                {
                    'temperature': {'value': 20.0, 'unit': 'celsius'},
                },
                ts='2026-02-04T12:00:00Z',
            ),
            make_payload(
                'INT-001',
                {
                    'temperature': {'value': 21.0, 'unit': 'celsius'},
                },
                ts='2026-02-04T12:01:00Z',
            ),
        ]

        ingest_telemetry_payload(payload=payloads, source='kafka')

        assert Telemetry.objects.filter(device_metric=dm_temp).count() == 2

    def test_mixed_batch_creates_only_valid(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Batch with valid + invalid items creates only valid Telemetry."""
        device, dm_temp, dm_door = setup_device_with_metrics

        payloads = [
            make_payload(
                'INT-001',
                {
                    'temperature': {'value': 22.5, 'unit': 'celsius'},
                },
            ),
            make_payload(
                'UNKNOWN-999',
                {
                    'temperature': {'value': 99.9, 'unit': 'celsius'},
                },
            ),
        ]

        ingest_telemetry_payload(payload=payloads, source='kafka')

        assert Telemetry.objects.filter(device_metric=dm_temp).count() == 1


# ──────────────────────────────────────────────
#  Validation errors
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
class TestValidationErrors:
    """E2E tests for payloads that fail validation."""

    def test_type_mismatch_creates_no_telemetry(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Numeric metric with string value is rejected."""
        device, dm_temp, dm_door = setup_device_with_metrics

        payload = make_payload(
            'INT-001',
            {
                'temperature': {'value': 'not-a-number', 'unit': 'celsius'},
            },
        )

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.filter(device_metric=dm_temp).count() == 0

    def test_unconfigured_metric_creates_no_telemetry(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Metric not configured for device is rejected."""
        device, dm_temp, dm_door = setup_device_with_metrics

        payload = make_payload(
            'INT-001',
            {
                'humidity': {'value': 55.0, 'unit': 'percent'},
            },
        )

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.count() == 0

    def test_invalid_schema_version_rejects_payload(
        self,
        mock_publish,
        setup_device_with_metrics,
    ):
        """Payload with wrong schema_version is rejected by serializer."""
        payload = {
            'schema_version': 999,
            'device': 'INT-001',
            'metrics': {'temperature': {'value': 22.5, 'unit': 'celsius'}},
            'ts': '2026-02-04T12:00:00Z',
        }

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.count() == 0


# ──────────────────────────────────────────────
#  Edge cases
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
class TestEdgeCases:
    """E2E tests for edge cases."""

    def test_invalid_payload_type_raises(self, mock_publish):
        """Non dict/list payload raises TypeError."""
        with pytest.raises(TypeError, match='payload must be of type dict or list'):
            ingest_telemetry_payload(payload='not-valid', source='mqtt')

    def test_empty_batch_returns_early(self, mock_publish):
        """Empty list payload is rejected by serializer."""
        ingest_telemetry_payload(payload=[], source='kafka')

        assert Telemetry.objects.count() == 0
