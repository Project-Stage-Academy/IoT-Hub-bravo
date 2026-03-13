"""
Integration tests: MQTT/Kafka payload → Celery task → Validate → Create → DB.

Tests call ingest_telemetry_payload directly with real DB to verify
the full ingestion pipeline end-to-end.
"""

from datetime import datetime, timezone, timedelta

import pytest
import fakeredis
from unittest.mock import patch

from apps.devices.models.telemetry import Telemetry
from apps.devices.tasks import ingest_telemetry_payload
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
)

pytestmark = pytest.mark.django_db


def make_payload(device_serial, metrics, ts=None):
    """Build a valid telemetry payload dict."""
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    return {
        'schema_version': 1,
        'device': device_serial,
        'metrics': metrics,
        'ts': ts,
    }


@pytest.fixture
def device():
    """Create an active device."""
    return DeviceFactory(serial_id='INT-001', is_active=True)


@pytest.fixture
def temp_metric():
    """Create a numeric temperature metric."""
    return MetricFactory(metric_type='temperature', data_type='numeric', unit='celsius')


@pytest.fixture
def door_metric():
    """Create a boolean door_open metric."""
    return MetricFactory(metric_type='door_open', data_type='bool', unit='open')


@pytest.fixture
def dm_temp(device, temp_metric):
    """Bind temperature metric to device."""
    return DeviceMetricFactory(device=device, metric=temp_metric)


@pytest.fixture
def dm_door(device, door_metric):
    """Bind door_open metric to device."""
    return DeviceMetricFactory(device=device, metric=door_metric)


# ──────────────────────────────────────────────
#  Single payload
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
@patch("apps.common.checker.idempotency_store.redis.Redis", fakeredis.FakeRedis)
class TestSinglePayload:
    """E2E tests for single dict payloads."""

    def test_valid_single_payload_creates_telemetry(
        self,
        mock_publish,
        dm_temp,
        dm_door,
    ):
        """Valid single payload creates Telemetry rows in DB."""
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
@patch("apps.common.checker.idempotency_store.redis.Redis", fakeredis.FakeRedis)
class TestBatchPayload:
    """E2E tests for batch (list) payloads."""

    def test_valid_batch_creates_all_telemetry(
        self,
        mock_publish,
        dm_temp,
    ):
        """Batch of valid payloads creates all Telemetry rows."""
        ts1 = datetime.now(timezone.utc).isoformat()
        ts2 = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
        payloads = [
            make_payload(
                'INT-001',
                {
                    'temperature': {'value': 20.0, 'unit': 'celsius'},
                },
                ts=ts1,
            ),
            make_payload(
                'INT-001',
                {
                    'temperature': {'value': 21.0, 'unit': 'celsius'},
                },
                ts=ts2,
            ),
        ]

        ingest_telemetry_payload(payload=payloads, source='kafka')

        assert Telemetry.objects.filter(device_metric=dm_temp).count() == 2

    def test_mixed_batch_creates_only_valid(
        self,
        mock_publish,
        dm_temp,
    ):
        """Batch with valid + invalid items creates only valid Telemetry."""
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
        dm_temp,
    ):
        """Numeric metric with string value is rejected."""
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
        device,
    ):
        """Metric not configured for device is rejected."""
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
    ):
        """Payload with wrong schema_version is rejected by serializer."""
        payload = {
            'schema_version': 999,
            'device': 'INT-001',
            'metrics': {'temperature': {'value': 22.5, 'unit': 'celsius'}},
            'ts': datetime.now(timezone.utc).isoformat(),
        }

        ingest_telemetry_payload(payload=payload, source='mqtt')

        assert Telemetry.objects.count() == 0


# ──────────────────────────────────────────────
#  Edge cases
# ──────────────────────────────────────────────


@patch('apps.devices.services.telemetry_services.publish_telemetry_event')
class TestEdgeCases:
    """E2E tests for edge cases."""

    def test_invalid_payload_type_logs_error(self, caplog):

        invalid_payload = "not-valid"

        with caplog.at_level("ERROR"):
            result = ingest_telemetry_payload(payload=invalid_payload, source="mqtt")

        assert result is None
        assert "payload must be of type dict or list" in caplog.text

    def test_empty_batch_returns_early(self, mock_publish):
        """Empty list payload is rejected by serializer."""
        ingest_telemetry_payload(payload=[], source='kafka')

        assert Telemetry.objects.count() == 0
