"""Integration tests for Device → Telemetry flow."""

import json
from unittest.mock import patch, MagicMock

import pytest

from apps.devices.models import Device, DeviceMetric, Telemetry
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


class TestTelemetryIngestPipeline:
    """Test telemetry ingestion pipeline with mocking."""

    @patch("apps.devices.models.Telemetry.objects.bulk_create")
    def test_ingest_calls_bulk_create_once(self, mock_bulk_create, client):
        """Test that telemetry ingestion calls bulk_create exactly once."""
        mock_bulk_create.return_value = []

        device = DeviceFactory(serial_id="MOCK-001")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric)

        payload = {
            "device": "MOCK-001",
            "metrics": {"temperature": "25.5"},
            "ts": "2024-01-15T10:30:00Z",
        }

        client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        mock_bulk_create.assert_called_once()

    @patch("apps.devices.models.Telemetry.objects.bulk_create")
    def test_ingest_bulk_create_receives_correct_count(self, mock_bulk_create, client):
        """Test that bulk_create receives correct number of telemetry objects."""
        mock_bulk_create.return_value = []

        device = DeviceFactory(serial_id="MOCK-002")
        metric1 = MetricFactory(metric_type="temperature", data_type="numeric")
        metric2 = MetricFactory(metric_type="humidity", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric1)
        DeviceMetricFactory(device=device, metric=metric2)

        payload = {
            "device": "MOCK-002",
            "metrics": {"temperature": "25.5", "humidity": "60"},
            "ts": "2024-01-15T10:30:00Z",
        }

        client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Verify bulk_create was called with 2 telemetry instances
        call_args = mock_bulk_create.call_args
        telemetry_list = call_args[0][0]  # First positional argument
        assert len(telemetry_list) == 2

    @patch("apps.devices.models.Device.objects.get")
    def test_ingest_calls_device_get(self, mock_device_get, client):
        """Test that ingestion looks up device by serial_id."""
        device = DeviceFactory(serial_id="MOCK-003")
        mock_device_get.return_value = device

        payload = {
            "device": "MOCK-003",
            "metrics": {"temperature": "25.5"},
            "ts": "2024-01-15T10:30:00Z",
        }

        client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        mock_device_get.assert_called_once_with(serial_id="MOCK-003")


class TestDeviceTelemetryFlow:
    """Test the full flow: Create Device → Add Metrics → Ingest Telemetry."""

    def test_full_device_telemetry_flow(self, client):
        """Test complete flow from device creation to telemetry ingestion."""
        # Step 1: Create a device
        device = DeviceFactory(serial_id="INTEGRATION-001", name="Integration Test Device")

        # Step 2: Create metrics and link to device
        temp_metric = MetricFactory(metric_type="temperature", data_type="numeric")
        humidity_metric = MetricFactory(metric_type="humidity", data_type="numeric")

        DeviceMetricFactory(device=device, metric=temp_metric)
        DeviceMetricFactory(device=device, metric=humidity_metric)

        # Step 3: Ingest telemetry via API
        payload = {
            "device": "INTEGRATION-001",
            "metrics": {
                "temperature": "25.5",
                "humidity": "60.0",
            },
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Step 4: Verify telemetry was created
        assert response.status_code == 201
        assert response.json()["created"] == 2

        # Step 5: Verify data in database
        telemetry_records = Telemetry.objects.filter(
            device_metric__device=device
        ).order_by("device_metric__metric__metric_type")

        assert telemetry_records.count() == 2

    def test_device_with_multiple_telemetry_timestamps(self, client):
        """Test device receiving telemetry at different timestamps."""
        device = DeviceFactory(serial_id="INTEGRATION-002")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric)

        # Ingest first reading
        response1 = client.post(
            "/api/telemetry/",
            data=json.dumps({
                "device": "INTEGRATION-002",
                "metrics": {"temperature": "20.0"},
                "ts": "2024-01-15T10:00:00Z",
            }),
            content_type="application/json",
        )
        assert response1.status_code == 201

        # Ingest second reading
        response2 = client.post(
            "/api/telemetry/",
            data=json.dumps({
                "device": "INTEGRATION-002",
                "metrics": {"temperature": "22.5"},
                "ts": "2024-01-15T11:00:00Z",
            }),
            content_type="application/json",
        )
        assert response2.status_code == 201

        # Verify both readings exist
        telemetry_count = Telemetry.objects.filter(
            device_metric__device=device
        ).count()
        assert telemetry_count == 2


class TestServiceLayerMocking:
    """Test service layer with mocked dependencies."""

    @patch("apps.devices.services.device_service.DeviceService.create_device")
    def test_device_create_api_calls_service(self, mock_create_device, client):
        """Test that POST /api/devices/ calls DeviceService.create_device."""
        user = UserFactory(role="admin")
        mock_device = DeviceFactory.build(id=999, name="Mocked Device")
        mock_create_device.return_value = mock_device

        import jwt
        from datetime import datetime, timedelta, timezone
        from django.conf import settings

        token = jwt.encode(
            {
                "sub": user.id,
                "role": "admin",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        payload = {
            "schema_version": "v1",
            "device": {
                "name": "Test Device",
                "serial_id": "SVC-001",
                "user_id": user.id,
            },
        }

        client.post(
            "/api/devices/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mock_create_device.assert_called_once()


# class TestTelemetryWithRules:
#     """Integration tests for Telemetry with Rules (placeholder for future)."""
#
#     @pytest.mark.skip(reason="Blocked: Rules engine not yet implemented")
#     def test_telemetry_triggers_rule(self, client):
#         """Test that telemetry above threshold triggers rule event."""
#         pass
#
#     @pytest.mark.skip(reason="Blocked: MQTT integration not yet implemented")
#     def test_mqtt_publishes_on_telemetry_ingest(self, client):
#         """Test that MQTT message is published when telemetry is ingested."""
#         pass
