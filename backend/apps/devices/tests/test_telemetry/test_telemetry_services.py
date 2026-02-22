import pytest
from apps.devices.models import Metric, DeviceMetric, Telemetry
from apps.devices.services.telemetry_services import telemetry_create


@pytest.mark.django_db
def test_telemetry_create_device_not_found(ts):
    payload = [
        {
            "device": "unknown-device",
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert "device" in result.errors
    assert "Missing serials" in result.errors["device"]
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_device_not_active(inactive_device, ts):
    payload = [
        {
            "device": inactive_device.serial_id,
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert "device" in result.errors
    assert "Missing serials" in result.errors["device"]
    assert Telemetry.objects.count() == 0

@pytest.mark.django_db
def test_telemetry_create_metric_does_not_exist(active_device, ts):
    DeviceMetric.objects.all().delete()
    Metric.objects.all().delete()

    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"},
                        "status": {"value": "ok", "unit": "Online"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert 0 in result.errors
    assert "temperature" in result.errors[0]
    assert "status" in result.errors[0]
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_metric_not_configured_for_device(active_device, metric_temperature_numeric, ts):
    DeviceMetric.objects.all().delete()

    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert 0 in result.errors
    assert "temperature" in result.errors[0]
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    'value',
    [True, '21.5', {'v': 21.5}],
)
def test_telemetry_create_type_mismatch_numeric(active_device, device_metric_numeric, ts, value):
    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {"temperature": {"value": value, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert 0 in result.errors
    assert "temperature" in result.errors[0]
    assert result.errors[0]["temperature"] in ("Type mismatch", "Unit mismatch")
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    'value',
    [1, 0.0, 'true'],
)
def test_telemetry_create_type_mismatch_bool(active_device, device_metric_bool, ts, value):
    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {"door_open": {"value": value, "unit": "open"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert 0 in result.errors
    assert "door_open" in result.errors[0]
    assert result.errors[0]["door_open"] in ("Type mismatch", "Unit mismatch")
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    'value',
    [1, False, 9.99],
)
def test_telemetry_create_type_mismatch_str(active_device, device_metric_str, ts, value):
    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {"status": {"value": value, "unit": "Online"}},
            "ts": ts,
        }
    ]
    result = telemetry_create(payload=payload)

    assert result.created_count == 0
    assert 0 in result.errors
    assert "status" in result.errors[0]
    assert result.errors[0]["status"] in ("Type mismatch", "Unit mismatch")
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_creates_rows_for_valid_metrics_only(
    active_device,
    device_metric_numeric,
    device_metric_bool,
    device_metric_str,
    ts,
):
    payload = [
        {
            "device": active_device.serial_id,
            "metrics": {
                "temperature": {"value": 21.5, "unit": "celsius"},
                "door_open": {"value": False, "unit": "open"},
                "status": {"value": "ok", "unit": "Online"},
                "unknown_metric": {"value": 123, "unit": ""},
            },
            "ts": ts,
        }
    ]

    result = telemetry_create(payload=payload)

    assert result.created_count == 3
    assert Telemetry.objects.count() == 3
    assert 0 in result.errors
    assert "unknown_metric" in result.errors[0]