from django.db import IntegrityError
import pytest

from apps.devices.models import Telemetry


@pytest.mark.django_db
def test_telemetry_unique_constraint_device_metric_ts(device_metric_numeric, ts):
    """Test duplicates for device_metric-ts raises error."""
    Telemetry.objects.create(
        device_metric=device_metric_numeric,
        ts=ts,
        value_jsonb={"t": "numeric", "v": 100},
    )

    with pytest.raises(IntegrityError):
        Telemetry.objects.create(
            device_metric=device_metric_numeric,
            ts=ts,
            value_jsonb={"t": "numeric", "v": 200},
        )


@pytest.mark.django_db
def test_telemetry_generated_numeric_value(device_metric_numeric, ts):
    """Test numeric column is generated from JSONB."""
    t = Telemetry.objects.create(
        device_metric=device_metric_numeric,
        ts=ts,
        value_jsonb={"t": "numeric", "v": 21.5},
    )

    assert t.value_numeric == 21.5
    assert t.value_bool is None
    assert t.value_str is None


@pytest.mark.django_db
def test_telemetry_generated_bool_value(device_metric_bool, ts):
    """Test bool column is generated from JSONB."""
    t = Telemetry.objects.create(
        device_metric=device_metric_bool,
        ts=ts,
        value_jsonb={"t": "bool", "v": True},
    )

    assert t.value_bool is True
    assert t.value_numeric is None
    assert t.value_str is None


@pytest.mark.django_db
def test_telemetry_generated_str_value(device_metric_str, ts):
    """Test str column is generated from JSONB."""
    t = Telemetry.objects.create(
        device_metric=device_metric_str,
        ts=ts,
        value_jsonb={"t": "str", "v": "ok"},
    )

    assert t.value_str == "ok"
    assert t.value_numeric is None
    assert t.value_bool is None


@pytest.mark.django_db
def test_telemetry_generated_values_are_none_for_unknown_type(
    device_metric_numeric, ts
):
    """Test unknown JSONB type leaves generated columns empty."""
    t = Telemetry.objects.create(
        device_metric=device_metric_numeric,
        ts=ts,
        value_jsonb={"t": "unknown-type", "v": "unknown-value"},
    )

    assert t.value_numeric is None
    assert t.value_bool is None
    assert t.value_str is None


@pytest.mark.django_db
def test_telemetry_sets_created_at_and_ts_defaults(device_metric_numeric):
    """Test created_at and ts defaults are applied when not provided."""
    t = Telemetry.objects.create(
        device_metric=device_metric_numeric,
        value_jsonb={"t": "numeric", "v": 21.5},
    )

    assert t.created_at is not None
    assert t.ts is not None
