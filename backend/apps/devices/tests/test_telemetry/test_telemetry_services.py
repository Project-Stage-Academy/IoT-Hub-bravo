import pytest
from unittest.mock import patch

from apps.devices.models import Metric, DeviceMetric, Telemetry
from apps.devices.services.telemetry_services import telemetry_create


@pytest.mark.django_db
def test_telemetry_create_device_not_found(ts):
    """Test unknown device returns error and creates nothing."""
    result = telemetry_create(
        device_serial_id="unknown-device",
        metrics={"temperature": 21.5},
        ts=ts,
    )

    assert result.created_count == 0
    assert result.errors == {"device": "Device not found."}
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_device_not_active(
    inactive_device,
    metric_temperature_numeric,
    ts,
):
    """Test inactive device returns error and creates nothing."""
    result = telemetry_create(
        device_serial_id=inactive_device.serial_id,
        metrics={"temperature": 21.5},
        ts=ts,
    )

    assert result.created_count == 0
    assert "device" in result.errors
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_no_metric_names(active_device, ts):
    """Test empty metrics dict returns error and creates nothing."""
    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={},
        ts=ts,
    )

    assert result.created_count == 0
    assert result.errors == {"metrics": "No valid metric names."}
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_metric_does_not_exist(active_device, ts):
    """Test missing metrics are reported and nothing is created."""
    DeviceMetric.objects.all().delete()
    Metric.objects.all().delete()

    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={
            "temperature": 21.5,
            "status": "ok",
        },
        ts=ts,
    )

    assert result.created_count == 0
    assert "temperature" in result.errors
    assert "status" in result.errors
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_metric_not_configured_for_device(
    active_device,
    metric_temperature_numeric,
    ts,
):
    """Test Metric exists but DeviceMetric object is missing."""
    DeviceMetric.objects.all().delete()

    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={"temperature": 21.5},
        ts=ts,
    )

    assert result.created_count == 0
    assert "temperature" in result.errors
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value,expected_error",
    [
        (True, "Type mismatch (expected numeric)"),
        ("21.5", "Type mismatch (expected numeric)"),
        ({"v": 21.5}, "Type mismatch (expected numeric)"),
    ],
)
def test_telemetry_create_type_mismatch_numeric(
    active_device,
    metric_temperature_numeric,
    device_metric_numeric,
    ts,
    value,
    expected_error,
):
    """Test numeric metric rejects non-numeric (and bool) values."""
    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={"temperature": value},
        ts=ts,
    )

    assert result.created_count == 0
    assert result.errors == {"temperature": expected_error}
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value,expected_error",
    [
        (1, "Type mismatch (expected bool)"),
        (0.0, "Type mismatch (expected bool)"),
        ("true", "Type mismatch (expected bool)"),
    ],
)
def test_telemetry_create_type_mismatch_bool(
    active_device,
    metric_door_open_bool,
    device_metric_bool,
    ts,
    value,
    expected_error,
):
    """Test bool metric rejects non-bool values."""
    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={"door_open": value},
        ts=ts,
    )

    assert result.created_count == 0
    assert result.errors == {"door_open": expected_error}
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value, expected_error",
    [
        (1, "Type mismatch (expected str)"),
        (False, "Type mismatch (expected str)"),
        (9.99, "Type mismatch (expected str)"),
    ],
)
def test_telemetry_create_type_mismatch_str(
    active_device,
    metric_status_str,
    device_metric_str,
    ts,
    value,
    expected_error,
):
    """Test str metric rejects non-string values."""
    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics={"status": value},
        ts=ts,
    )

    assert result.created_count == 0
    assert result.errors == {"status": expected_error}
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@patch("apps.devices.services.telemetry_services.publish_telemetry_event")
def test_telemetry_create_creates_rows_for_valid_metrics_only(
    mock_publish_telemetry_event,
    active_device,
    metric_temperature_numeric,
    metric_door_open_bool,
    metric_status_str,
    device_metric_numeric,
    device_metric_bool,
    device_metric_str,
    ts,
):
    """
    Test service creates telemetry only for valid
    metric-value pairs and reports errors for others.
    """
    metrics = {
        "temperature": 21.5,
        "door_open": True,
        "status": 1,
        "unknown_metric": 123,
    }

    result = telemetry_create(
        device_serial_id=active_device.serial_id,
        metrics=metrics,
        ts=ts,
    )

    assert result.created_count == 2
    assert Telemetry.objects.count() == 2
    assert "unknown_metric" in result.errors
    assert "status" in result.errors
