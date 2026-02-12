"""Unit tests for Telemetry model."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.devices.models import Telemetry
from tests.fixtures.factories import (
    DeviceMetricFactory,
    TelemetryFactory,
    TelemetryBooleanFactory,
    TelemetryStringFactory,
)


pytestmark = pytest.mark.django_db


class TestTelemetryCreation:
    """Tests for Telemetry model creation."""

    def test_create_telemetry_with_numeric_value(self):
        """Test creating telemetry with numeric value."""
        telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "42.5"})

        assert telemetry.id is not None
        assert telemetry.value_jsonb == {"t": "numeric", "v": "42.5"}

    def test_create_telemetry_with_boolean_value(self):
        """Test creating telemetry with boolean value."""
        telemetry = TelemetryBooleanFactory()

        assert telemetry.value_jsonb["t"] == "bool"

    def test_create_telemetry_with_string_value(self):
        """Test creating telemetry with string value."""
        telemetry = TelemetryStringFactory()

        assert telemetry.value_jsonb["t"] == "str"

    def test_telemetry_has_timestamp(self):
        """Test that telemetry has auto-generated timestamp."""
        telemetry = TelemetryFactory()

        assert telemetry.ts is not None
        assert telemetry.created_at is not None


class TestTelemetryGeneratedFields:
    """Tests for Telemetry generated fields (value_numeric, value_bool, value_str)."""

    def test_value_numeric_generated_for_numeric_type(self):
        """Test that value_numeric is populated for numeric telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "25.5"})
        telemetry.refresh_from_db()

        assert telemetry.value_numeric is not None
        assert float(telemetry.value_numeric) == 25.5

    def test_value_bool_generated_for_bool_type(self):
        """Test that value_bool is populated for boolean telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "bool", "v": "true"})
        telemetry.refresh_from_db()

        assert telemetry.value_bool is True

    def test_value_str_generated_for_str_type(self):
        """Test that value_str is populated for string telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "str", "v": "active"})
        telemetry.refresh_from_db()

        assert telemetry.value_str == "active"

    def test_value_numeric_none_for_non_numeric(self):
        """Test that value_numeric is None for non-numeric telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "str", "v": "test"})
        telemetry.refresh_from_db()

        assert telemetry.value_numeric is None


class TestTelemetryConstraints:
    """Tests for Telemetry model constraints."""

    def test_unique_device_metric_timestamp(self):
        """Test that device_metric + timestamp combination must be unique."""
        device_metric = DeviceMetricFactory()
        fixed_time = timezone.now()

        TelemetryFactory(device_metric=device_metric, ts=fixed_time)

        with pytest.raises(IntegrityError):
            TelemetryFactory(device_metric=device_metric, ts=fixed_time)

    def test_same_device_metric_different_timestamps_allowed(self):
        """Test that same device_metric can have multiple telemetry at different times."""
        from datetime import timedelta

        device_metric = DeviceMetricFactory()
        time1 = timezone.now()
        time2 = time1 + timedelta(seconds=1)

        t1 = TelemetryFactory(device_metric=device_metric, ts=time1)
        t2 = TelemetryFactory(device_metric=device_metric, ts=time2)

        assert t1.device_metric == t2.device_metric
        assert t1.ts != t2.ts


class TestTelemetryRelationships:
    """Tests for Telemetry foreign key behavior."""

    def test_cascade_delete_on_device_metric(self):
        """Test that deleting device_metric cascades to telemetry."""
        telemetry = TelemetryFactory()
        device_metric = telemetry.device_metric
        telemetry_id = telemetry.id

        device_metric.delete()

        assert not Telemetry.objects.filter(id=telemetry_id).exists()


class TestTelemetryFormattedValue:
    """Tests for Telemetry.formatted_value() helper method."""

    def test_formatted_value_numeric(self):
        """Test formatted_value returns formatted number for numeric telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "25.5"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value()

        assert result == "25.500"

    def test_formatted_value_numeric_custom_precision(self):
        """Test formatted_value respects precision parameter."""
        telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "25.12345"})
        telemetry.refresh_from_db()

        assert telemetry.formatted_value(precision=1) == "25.1"
        assert telemetry.formatted_value(precision=4) == "25.1234"

    def test_formatted_value_boolean(self):
        """Test formatted_value returns string for boolean telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "bool", "v": "true"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value()

        assert result == "True"

    def test_formatted_value_string(self):
        """Test formatted_value returns string value for string telemetry."""
        telemetry = TelemetryFactory(value_jsonb={"t": "str", "v": "active"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value()

        assert result == "active"

    def test_formatted_value_empty_when_no_value(self):
        """Test formatted_value returns empty string when no value extracted."""
        telemetry = TelemetryFactory(value_jsonb={"t": "unknown", "v": "test"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value()

        assert result == ""


class TestTelemetryFormattedValueWithType:
    """Tests for Telemetry.formatted_value_with_type() helper method."""

    def test_formatted_value_with_type_numeric(self):
        """Test formatted_value_with_type includes type label for numeric."""
        telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "25.5"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value_with_type()

        assert result == "25.500 (numeric)"

    def test_formatted_value_with_type_boolean(self):
        """Test formatted_value_with_type includes type label for boolean."""
        telemetry = TelemetryFactory(value_jsonb={"t": "bool", "v": "true"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value_with_type()

        assert result == "True (bool)"

    def test_formatted_value_with_type_string(self):
        """Test formatted_value_with_type includes type label for string."""
        telemetry = TelemetryFactory(value_jsonb={"t": "str", "v": "active"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value_with_type()

        assert result == "active (str)"

    def test_formatted_value_with_type_empty_when_no_value(self):
        """Test formatted_value_with_type returns empty string when no value."""
        telemetry = TelemetryFactory(value_jsonb={"t": "unknown", "v": "test"})
        telemetry.refresh_from_db()

        result = telemetry.formatted_value_with_type()

        assert result == ""
