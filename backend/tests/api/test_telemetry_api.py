"""API tests for Telemetry ingest endpoint."""

import json

import pytest

from apps.devices.models import Telemetry
from tests.fixtures.factories import DeviceFactory, DeviceMetricFactory, MetricFactory


pytestmark = pytest.mark.django_db


class TestTelemetryIngestAPI:
    """Tests for POST /api/telemetry/"""

    def test_ingest_telemetry_success(self, client):
        """Test successful telemetry ingestion."""
        device = DeviceFactory(serial_id="DEVICE-001")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric)

        payload = {
            "device": "DEVICE-001",
            "metrics": {"temperature": "25.5"},
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["created"] == 1

    def test_ingest_telemetry_multiple_metrics(self, client):
        """Test ingesting multiple metrics at once."""
        device = DeviceFactory(serial_id="DEVICE-002")
        metric1 = MetricFactory(metric_type="temperature", data_type="numeric")
        metric2 = MetricFactory(metric_type="humidity", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric1)
        DeviceMetricFactory(device=device, metric=metric2)

        payload = {
            "device": "DEVICE-002",
            "metrics": {"temperature": "25.5", "humidity": "60"},
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        assert response.json()["created"] == 2

    def test_ingest_telemetry_device_not_found(self, client):
        """Test 404 when device doesn't exist."""
        payload = {
            "device": "NON-EXISTENT",
            "metrics": {"temperature": "25.5"},
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 404
        assert "device not found" in response.json()["error"]

    def test_ingest_telemetry_invalid_json(self, client):
        """Test 400 for invalid JSON."""
        response = client.post(
            "/api/telemetry/",
            data="not valid json",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "invalid json" in response.json()["error"]

    def test_ingest_telemetry_missing_required_fields(self, client):
        """Test 400 when required fields are missing."""
        payload = {"device": "DEVICE-001"}

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "invalid payload" in response.json()["error"]

    def test_ingest_telemetry_invalid_timestamp(self, client):
        """Test 400 for invalid timestamp format."""
        device = DeviceFactory(serial_id="DEVICE-003")

        payload = {
            "device": "DEVICE-003",
            "metrics": {"temperature": "25.5"},
            "ts": "not-a-timestamp",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "timestamp" in response.json()["error"]

    def test_ingest_telemetry_method_not_allowed(self, client):
        """Test that GET method is not allowed."""
        response = client.get("/api/telemetry/")

        assert response.status_code == 405

    def test_ingest_telemetry_unknown_metric_ignored(self, client):
        """Test that unknown metrics are silently ignored."""
        device = DeviceFactory(serial_id="DEVICE-004")
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric)

        payload = {
            "device": "DEVICE-004",
            "metrics": {"temperature": "25.5", "unknown_metric": "100"},
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        assert response.json()["created"] == 1