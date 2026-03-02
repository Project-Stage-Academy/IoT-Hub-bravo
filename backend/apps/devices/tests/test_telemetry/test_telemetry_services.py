import pytest
from apps.devices.models import Metric, DeviceMetric, Telemetry
from apps.devices.services.telemetry_services import telemetry_create, telemetry_validate


@pytest.mark.django_db
def test_telemetry_create_device_not_found(ts):
    payload = [
        {
            "device_serial_id": "unknown-device",
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload=payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    device_errors = [e for e in result.errors if e["field"] == "device"]
    assert device_errors
    assert any("Missing serials" in e["error"] for e in device_errors)
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_device_not_active(inactive_device, ts):
    payload = [
        {
            "device_serial_id": inactive_device.serial_id,
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    device_errors = [e for e in result.errors if e["field"] == "device"]
    assert device_errors
    assert any("Missing serials" in e["error"] for e in device_errors)
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_metric_does_not_exist(active_device, ts):
    DeviceMetric.objects.all().delete()
    Metric.objects.all().delete()

    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {
                "temperature": {"value": 21.5, "unit": "celsius"},
                "status": {"value": "ok", "unit": "Online"},
            },
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    metric_errors = [e for e in result.errors if e["index"] == 0]
    fields = [e["field"] for e in metric_errors]
    assert "temperature" in fields
    assert "status" in fields
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
def test_telemetry_create_metric_not_configured_for_device(
    active_device, metric_temperature_numeric, ts
):
    DeviceMetric.objects.all().delete()

    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"temperature": {"value": 21.5, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    metric_errors = [e for e in result.errors if e["index"] == 0]
    fields = [e["field"] for e in metric_errors]
    assert "temperature" in fields
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("value", [True, "21.5", {"v": 21.5}])
def test_telemetry_create_type_mismatch_numeric(active_device, device_metric_numeric, ts, value):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"temperature": {"value": value, "unit": "celsius"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    metric_errors = [e for e in result.errors if e["index"] == 0 and e["field"] == "temperature"]
    assert metric_errors
    assert metric_errors[0]["error"] in ("Type mismatch", "Unit mismatch")
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("value", [1, 0.0, "true"])
def test_telemetry_create_type_mismatch_bool(active_device, device_metric_bool, ts, value):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"door_open": {"value": value, "unit": "open"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    metric_errors = [e for e in result.errors if e["index"] == 0 and e["field"] == "door_open"]
    assert metric_errors
    assert metric_errors[0]["error"] in ("Type mismatch", "Unit mismatch")
    assert Telemetry.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("value", [1, False, 9.99])
def test_telemetry_create_type_mismatch_str(active_device, device_metric_str, ts, value):
    payload = [
        {
            "device_serial_id": active_device.serial_id,
            "metrics": {"status": {"value": value, "unit": "Online"}},
            "ts": ts,
        }
    ]
    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 0
    metric_errors = [e for e in result.errors if e["index"] == 0 and e["field"] == "status"]
    assert metric_errors
    assert metric_errors[0]["error"] in ("Type mismatch", "Unit mismatch")
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
            "device_serial_id": active_device.serial_id,
            "metrics": {
                "temperature": {"value": 21.5, "unit": "celsius"},
                "door_open": {"value": False, "unit": "open"},
                "status": {"value": "ok", "unit": "Online"},
                "unknown_metric": {"value": 123, "unit": ""},
            },
            "ts": ts,
        }
    ]

    validation = telemetry_validate(payload)
    result = telemetry_create(
        valid_data=validation.validated_rows, validation_errors=validation.errors
    )

    assert result.created_count == 3
    assert Telemetry.objects.count() == 3

    unknown_errors = [
        e for e in result.errors if e["index"] == 0 and e["field"] == "unknown_metric"
    ]
    assert unknown_errors
