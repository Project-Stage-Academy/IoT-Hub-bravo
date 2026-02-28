from django.utils import timezone
import pytest

from apps.devices.serializers.telemetry_serializers import (
    TelemetryCreateSerializer,
    TelemetryBatchCreateSerializer,
)


def test_create_serializer_valid_payload(valid_telemetry_payload):
    """Test valid payload passes validation and returns correct fields."""
    s = TelemetryCreateSerializer(valid_telemetry_payload)
    assert s.is_valid() is True
    data = s.validated_data

    assert set(data.keys()) == {"device_serial_id", "metrics", "ts"}
    assert data["device_serial_id"] == "DEV-001"
    assert data["metrics"]["temperature"] == 21.5
    assert data["metrics"]["door_open"] is False
    assert data["metrics"]["status"] == "ok"
    assert timezone.is_aware(data["ts"]) is True


def test_create_serializer_rejects_non_dict_payload():
    """Test non-dict payload is rejected."""
    s = TelemetryCreateSerializer(["not-a-dict"])

    assert s.is_valid() is False
    assert s.errors["non_field_errors"] == "Payload must be a JSON object."


@pytest.mark.parametrize(
    "missing_field",
    ["schema_version", "device", "metrics", "ts"],
)
def test_create_serializer_missing_required_field(
    valid_telemetry_payload, missing_field
):
    """Test missing required field returns an error."""
    payload = valid_telemetry_payload
    payload.pop(missing_field)

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert missing_field in s.errors
    assert s.errors[missing_field] == f"{missing_field} field is required."


@pytest.mark.parametrize(
    "field, invalid_value, expected_type",
    [
        ("schema_version", "1", "int"),
        ("device", 123, "str"),
        ("metrics", "not-a-dict", "dict"),
        ("ts", 123, "str"),
    ],
)
def test_create_serializer_wrong_field_types(
    valid_telemetry_payload, field, invalid_value, expected_type
):
    """Test wrong field types are rejected with error messages."""
    payload = valid_telemetry_payload
    payload[field] = invalid_value

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert field in s.errors
    assert s.errors[field] == f"{field} must be of type {expected_type}."


def test_unsupported_schema_version(valid_telemetry_payload):
    """Test unsupported schema_version returns an error."""
    payload = valid_telemetry_payload
    payload["schema_version"] = 999

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "schema_version" in s.errors


@pytest.mark.parametrize("device_value", ["", "   ", "\n\t"])
def test_device_must_be_non_empty_string(valid_telemetry_payload, device_value):
    """Test device must be a non-empty string after trimming."""
    payload = valid_telemetry_payload
    payload["device"] = device_value

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "device" in s.errors


def test_metrics_rejects_invalid_metric_names(valid_telemetry_payload):
    """Test invalid metric names produce per-metric errors."""
    payload = valid_telemetry_payload
    payload["metrics"] = {"": 1, " invalid ": 2, 123: 3}

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "metrics" in s.errors
    assert "" in s.errors["metrics"] or " " in s.errors["metrics"]
    assert "123" in s.errors["metrics"]


def test_create_serializer_metrics_rejects_invalid_metric_value_types(
    valid_telemetry_payload,
):
    """Test metric values must be bool/int/float/str."""
    payload = valid_telemetry_payload
    payload["metrics"] = {"temperature": {"nested": "object"}}

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "metrics" in s.errors


def test_create_serializer_ts_must_be_non_empty(valid_telemetry_payload):
    """Test ts must be a non-empty string."""
    payload = dict(valid_telemetry_payload)
    payload["ts"] = "   "

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "ts" in s.errors


def test_create_serializer_ts_must_be_valid_iso8601(valid_telemetry_payload):
    """Test invalid ISO-8601 ts is rejected."""
    payload = valid_telemetry_payload
    payload["ts"] = "not-a-datetime"

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is False
    assert "ts" in s.errors


def test_naive_ts_becomes_aware(valid_telemetry_payload):
    """Test naive datetime string is converted to timezone-aware."""
    payload = valid_telemetry_payload
    payload["ts"] = "2026-02-05T10:00:00"

    s = TelemetryCreateSerializer(payload)
    assert s.is_valid() is True
    assert timezone.is_aware(s.validated_data["ts"]) is True


def test_batch_serializer_rejects_non_list_payload():
    """Test batch serializer rejects non-list payload."""
    s = TelemetryBatchCreateSerializer({"not": "a list"})
    assert s.is_valid() is False
    assert "non_field_errors" in s.errors


def test_batch_serializer_accepts_mixed_valid_and_invalid_items(
    valid_telemetry_payload,
):
    """Test batch serializer returns validated items and collects item_errors."""
    invalid_item = dict(valid_telemetry_payload)
    invalid_item["device"] = {"not": "a valid device"}

    payload = [valid_telemetry_payload, invalid_item, valid_telemetry_payload]

    s = TelemetryBatchCreateSerializer(payload)
    assert s.is_valid() is False

    assert len(s.valid_items) == 2
    assert s.valid_items[0]["device_serial_id"] == "DEV-001"
    assert s.valid_items[1]["device_serial_id"] == "DEV-001"

    assert s.item_errors
    assert 1 in s.item_errors
    assert "device" in s.item_errors[1]


def test_batch_serializer_all_invalid_items_returns_errors(valid_telemetry_payload):
    """Test batch serializer with all invalid items returns errors and no validated data."""
    invalid_item1 = dict(valid_telemetry_payload)
    invalid_item1["device"] = {"not": "a valid device"}

    invalid_item2 = dict(valid_telemetry_payload)
    invalid_item2["ts"] = "invalid-time"

    s = TelemetryBatchCreateSerializer([invalid_item1, invalid_item2])
    assert s.is_valid() is False

    assert "items" in s.errors
    assert 0 in s.errors["items"]
    assert 1 in s.errors["items"]
    assert "device" in s.errors["items"][0]
    assert "ts" in s.errors["items"][1]


def test_batch_serializer_empty_list_returns_empty_batch_error():
    """Test empty batch returns errors."""
    s = TelemetryBatchCreateSerializer([])

    assert s.is_valid() is False
    assert "items" in s.errors
    assert s.errors["items"]["non_field_errors"] == "Empty batch."
