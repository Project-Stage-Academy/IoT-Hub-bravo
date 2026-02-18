import pytest

from validator.telemetry_validator import TelemetryValidator
from apps.devices.models import Device, Metric, DeviceMetric
from apps.users.models import User


valid_data = """{
        "schema_version": 1,
        "device": "SN-B2-TEMP-0101",
        "metrics": {
            "humidity": 99
        },
        "ts": "2026-01-25 11:00"
    }
"""
@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="client", email="client@example.com", password="password123", role="client"
    )


@pytest.fixture
def active_device(client_user, db):
    return Device.objects.create(
        serial_id="SN-B2-TEMP-0101",
        name="Active Device",
        user=client_user,
        is_active=True
    )


@pytest.fixture
def humidity_metric(db):
    return Metric.objects.create(
        metric_type="humidity",
        data_type="numeric",
    )


@pytest.fixture
def device_metric(db, active_device, humidity_metric):
    return DeviceMetric.objects.create(
        device=active_device,
        metric=humidity_metric,
    )


def test_validator_valid_data(active_device, device_metric):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={"humidity": 99},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is True
    assert validator.errors == {}
    assert "humidity" in validator.validated_metrics

def test_validator_device_not_found(db):
    validator = TelemetryValidator(
        device_serial_id="UNKNOWN",
        metrics={"humidity": 99},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert "device" in validator.errors

def test_validator_device_not_active(client_user, db):
    Device.objects.create(
        serial_id="SN-B2-TEMP-0101",
        name="Inactive Device",
        user=client_user,
        is_active=False,
    )

    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={"humidity": 99},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert validator.errors["device"] == "Device is not active."

def test_validator_metric_not_defined(active_device):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={"temperature": 25},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert "temperature" in validator.errors

def test_validator_metric_not_associated(active_device, humidity_metric):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={"humidity": 99},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert "humidity" in validator.errors

def test_validator_wrong_data_type(active_device, device_metric):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={"humidity": "high"},
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert "humidity" in validator.errors

def test_validator_metrics_not_dict(active_device):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics=["humidity"],
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert "metrics" in validator.errors

def test_validator_collects_multiple_errors(active_device):
    validator = TelemetryValidator(
        device_serial_id="SN-B2-TEMP-0101",
        metrics={
            "unknown_metric": 10,
            "humidity": "bad_type",
        },
        ts="2026-01-25 11:00",
    )

    assert validator.is_valid() is False
    assert len(validator.errors) == 2
