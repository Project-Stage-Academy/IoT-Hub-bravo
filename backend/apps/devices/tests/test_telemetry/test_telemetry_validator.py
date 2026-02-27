import pytest

from datetime import datetime
from validator.telemetry_validator import TelemetryBatchValidator
from apps.devices.models import Device, Metric, DeviceMetric
from apps.users.models import User


@pytest.fixture
def temperature_metric():
    return Metric.objects.create(
        metric_type="temperature",
        unit="celsius",
        data_type="numeric",
    )


@pytest.fixture
def second_device(client_user):
    return Device.objects.create(
        serial_id="SN-B2-TEMP-0202",
        name="Second Device",
        user=client_user,
        is_active=True,
    )


@pytest.fixture
def second_device_metric(second_device, temperature_metric):
    return DeviceMetric.objects.create(
        device=second_device,
        metric=temperature_metric,
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="client",
        email="client@example.com",
        password="password123",
        role="client",
    )


@pytest.fixture
def active_device(client_user):
    return Device.objects.create(
        serial_id="SN-B2-TEMP-0101",
        name="Active Device",
        user=client_user,
        is_active=True,
    )


@pytest.fixture
def humidity_metric():
    return Metric.objects.create(
        metric_type="humidity",
        unit="percent",
        data_type="numeric",
    )


@pytest.fixture
def device_metric(active_device, humidity_metric):
    return DeviceMetric.objects.create(
        device=active_device,
        metric=humidity_metric,
    )


@pytest.mark.django_db
def test_batch_validator_success(
    active_device, device_metric, second_device, second_device_metric
):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"humidity": {"value": 55, "unit": "percent"}},
            "ts": datetime(2026, 1, 25, 11, 0),
        },
        {
            "device_serial_id": second_device.serial_id,
            "metrics": {"temperature": {"value": 22.5, "unit": "celsius"}},
            "ts": datetime(2026, 1, 25, 11, 5),
        },
    ]

    validator = TelemetryBatchValidator(payload)
    assert validator.is_valid() is True
    assert len(validator.validated_rows) == 2
    assert validator.errors == []


@pytest.mark.django_db
def test_batch_validator_missing_device(active_device, device_metric):
    payload = [
        {
            "device_serial_id": "NON_EXISTENT",
            "metrics": {"humidity": {"value": 55, "unit": "percent"}},
            "ts": datetime(2026, 1, 25, 11, 0),
        }
    ]
    validator = TelemetryBatchValidator(payload)
    assert validator.is_valid() is False
    device_errors = [e for e in validator.errors if e["field"] == "device"]
    assert device_errors
    assert "NON_EXISTENT" in device_errors[0]["error"]


@pytest.mark.django_db
def test_batch_validator_unit_mismatch(active_device, device_metric):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"humidity": {"value": 55, "unit": "wrong_unit"}},
            "ts": datetime(2026, 1, 25, 11, 0),
        }
    ]
    validator = TelemetryBatchValidator(payload)
    assert validator.is_valid() is False
    metric_errors = [e for e in validator.errors if e["index"] == 0 and e["field"] == "humidity"]
    assert metric_errors
    assert metric_errors[0]["error"] == "Unit mismatch"


@pytest.mark.django_db
def test_batch_validator_type_mismatch(active_device, device_metric):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"humidity": {"value": "not_numeric", "unit": "percent"}},
            "ts": datetime(2026, 1, 25, 11, 0),
        }
    ]
    validator = TelemetryBatchValidator(payload)
    assert validator.is_valid() is False
    metric_errors = [e for e in validator.errors if e["index"] == 0 and e["field"] == "humidity"]
    assert metric_errors
    assert metric_errors[0]["error"] == "Type mismatch"


@pytest.mark.django_db
def test_batch_validator_multiple_metrics(active_device, device_metric, temperature_metric):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {
                "humidity": {"value": 61, "unit": "percent"},
                "temperature": {"value": 33.3, "unit": "celsius"},
            },
            "ts": datetime(2026, 1, 25, 11, 10),
        }
    ]
    validator = TelemetryBatchValidator(payload)
    assert validator.is_valid() is False
    metric_errors = [
        e for e in validator.errors if e["index"] == 0 and e["field"] == "temperature"
    ]
    assert metric_errors
    assert metric_errors[0]["error"] == "Metric not configured"
    validated_metrics = [r["device_metric_id"] for r in validator.validated_rows]
    assert len(validated_metrics) == 1
