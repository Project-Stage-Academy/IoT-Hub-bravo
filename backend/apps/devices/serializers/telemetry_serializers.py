import datetime
from typing import Optional, Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime


class BaseSerializer:
    def __init__(self, data: Any):
        self.initial_data = data
        self._validated_data: Optional[Any] = None
        self._errors: dict[str, Any] = {}

    @property
    def validated_data(self):
        if self._validated_data is None:
            raise ValueError("Call is_valid() before accessing validated_data.")
        return self._validated_data

    @property
    def errors(self) -> dict[str, Any]:
        return self._errors

    def is_valid(self) -> bool:
        self._errors = {}
        self._validated_data = self._validate(self.initial_data)
        return not self._errors

    def _validate(self, data: Any):
        raise NotImplementedError


class TelemetryCreateSerializer(BaseSerializer):
    SCHEMA_VERSION = 1
    METRIC_VALUE_TYPES = (bool, int, float, str)

    REQUIRED_FIELDS = {
        "schema_version": int,
        "device": str,
        "metrics": dict,
        "ts": str,
    }

    def _validate(self, data: Any) -> Optional[dict[str, Any]]:
        if not isinstance(data, dict):
            self._errors["non_field_errors"] = "Payload must be a JSON object."
            return None

        self._validate_required_fields(data)
        if self._errors:
            return None

        if data["schema_version"] != self.SCHEMA_VERSION:
            self._errors["schema_version"] = (
                f"Unsupported schema_version: {data['schema_version']}. "
                f"Supported: {self.SCHEMA_VERSION}."
            )
            return None

        device = self._validate_device(data["device"])
        metrics = self._validate_metrics(data["metrics"])
        ts = self._validate_ts(data["ts"])

        if self._errors:
            return None

        return {
            "device_serial_id": device,
            "metrics": metrics,
            "ts": ts,
        }

    def _validate_required_fields(self, data: dict):
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in data:
                self._errors[field] = f"{field} field is required."
            elif not isinstance(data[field], expected_type):
                self._errors[field] = f"{field} must be of type {expected_type.__name__}."

    def _validate_device(self, value: str) -> Optional[str]:
        value = value.strip()
        if not value:
            self._errors["device"] = "device must be a non-empty string."
            return None
        return value

    def _validate_metrics(self, metrics_raw: dict) -> Optional[dict[str, Any]]:
        if not metrics_raw:
            self._errors["metrics"] = {"non_field_errors": "Metrics cannot be empty."}
            return None

        validated = {}
        errors = {}

        for name, metric_data in metrics_raw.items():
            if not isinstance(name, str) or not name.strip():
                errors[str(name)] = "Metric name must be a non-empty string."
                continue

            if not isinstance(metric_data, dict):
                errors[name] = "Metric must be a dictionary with 'value' and 'unit'."
                continue
            if "value" not in metric_data or "unit" not in metric_data:
                errors[name] = "Metric must contain both 'value' and 'unit' keys."
                continue

            value = metric_data.get("value")
            unit = metric_data.get("unit")

            if not isinstance(value, self.METRIC_VALUE_TYPES):
                errors[name] = "Metric value must be bool/int/float/str."
                continue

            if not isinstance(unit, str) or not unit.strip():
                errors[name] = "Metric unit must be a non-empty string."
                continue

            validated[name.strip()] = {
                "value": value,
                "unit": unit.strip(),
            }

        if errors:
            self._errors["metrics"] = errors
            return None

        return validated

    def _validate_ts(self, ts_raw: str) -> Optional[datetime.datetime]:
        ts_raw = ts_raw.strip()
        if not ts_raw:
            self._errors["ts"] = "ts must be a non-empty ISO-8601 datetime string."
            return None

        ts = parse_datetime(ts_raw)
        if ts is None:
            self._errors["ts"] = (
                "ts must be a valid ISO-8601 datetime " "(e.g. 2026-02-19T11:52:45Z)."
            )
            return None

        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts, timezone.get_default_timezone())

        ts = ts.astimezone(datetime.timezone.utc)

        ts = ts.replace(microsecond=0)

        return ts

    def validate_producer_message(self):
        self._errors = {}
        self._validated_data = None

        dm_id = self.initial_data.get("device_metric_id")
        ts_raw = self.initial_data.get("ts")
        values_jsonb = self.initial_data.get("value_jsonb")

        if not isinstance(dm_id, int):
            self._errors["device_metric_id"] = "Must be integer"

        ts = self._validate_ts(ts_raw)

        if not isinstance(values_jsonb, dict):
            self._errors["value_jsonb"] = "Must be dict"
            return False

        type_ = values_jsonb.get("t")
        value = values_jsonb.get("v")

        if type_ is None:
            self._errors["value_jsonb.t"] = "Type is required"

        if value is None:
            self._errors["value_jsonb.v"] = "Value is required"

        if self._errors:
            return False

        self._validated_data = {
            "device_metric_id": dm_id,
            "ts": ts,
            "value_jsonb": {
                "t": type_,
                "v": value,
            },
        }

        return True


class TelemetryBatchCreateSerializer(BaseSerializer):
    def __init__(self, data: Any):
        super().__init__(data)
        self._valid_items = []
        self._item_errors = {}

    @property
    def valid_items(self):
        return self._valid_items

    @property
    def item_errors(self):
        return self._item_errors

    def _validate(self, data: Any):
        self._valid_items = []
        self._item_errors = {}
        if not isinstance(data, list):
            self._errors["non_field_errors"] = "Payload must be a JSON array."
            return None

        if not data:
            self._errors["items"] = {"non_field_errors": "Empty batch."}
            return None

        for index, item in enumerate(data):
            serializer = TelemetryCreateSerializer(item)
            if serializer.is_valid():
                self._valid_items.append(serializer.validated_data)
            else:
                self._item_errors[index] = serializer.errors

        if self._item_errors:
            self._errors["items"] = self._item_errors
            return None

        return self._valid_items

    def validate_producer_batch(self):
        self._valid_items = []
        self._item_errors = {}
        self._errors = {}

        if not isinstance(self.initial_data, list):
            self._errors["non_field_errors"] = "Payload must be a JSON array."
            return None

        for index, item in enumerate(self.initial_data):
            serializer = TelemetryProducerMessageSerializer(item)

            if serializer.is_valid():
                self._valid_items.append(serializer.validated_data)
            else:
                self._item_errors[index] = serializer.errors

        if self._item_errors:
            self._errors["items"] = self._item_errors

        return self._valid_items, self._item_errors


# TODO: Refactor this and add a parent class JSONSerializer
class TelemetryProducerMessageSerializer:

    REQUIRED_FIELDS: dict[str, type] = {
        "device_serial_id": str,
        "device_metric_id": int,
        "ts": str,
        "value_jsonb": dict,
    }

    OPTIONAL_FIELDS: dict[str, type] = {}

    STRICT: bool = True

    VALUE_JSONB_REQUIRED_FIELDS = {
        "t": str,
        "v": (bool, int, float, str),
    }

    def __init__(self, data: Any):
        self.initial_data = data
        self._errors: dict[str, Any] = {}
        self.validated_data: Optional[dict[str, Any]] = None

    @property
    def errors(self):
        return self._errors

    def is_valid(self) -> bool:
        validated = self._validate(self.initial_data)

        if self._errors:
            return False

        self.validated_data = validated
        return True

    def _validate(self, data: Any) -> Optional[dict[str, Any]]:

        if not isinstance(data, dict):
            self._errors["non_field_errors"] = "Payload must be a JSON object."
            return None

        self._validate_field_map(data, self.REQUIRED_FIELDS, required=True)
        self._validate_field_map(data, self.OPTIONAL_FIELDS, required=False)

        if self.STRICT:
            self._validate_no_unknown_fields(data)

        if self._errors:
            return None

        validated = self._validate_fields(data)

        if self._errors:
            return None

        return validated

    def _validate_field_map(
        self,
        data: dict[str, Any],
        fields: dict[str, type],
        *,
        required: bool,
    ) -> None:

        for field, expected_type in fields.items():

            if field not in data:
                if required:
                    self._errors[field] = f"{field} field is required."
                continue

            value = data[field]

            if value is None and not required:
                continue

            if not isinstance(value, expected_type):
                self._errors[field] = f"{field} must be of type {expected_type.__name__}."

    def _validate_no_unknown_fields(self, data: dict[str, Any]) -> None:

        allowed = set(self.REQUIRED_FIELDS) | set(self.OPTIONAL_FIELDS)
        unknown = set(data) - allowed

        if unknown:
            self._errors["non_field_errors"] = f"Unknown fields: {sorted(unknown)}"

    def _validate_fields(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:

        ts = self._validate_ts(data["ts"])
        value_jsonb = self._validate_value_jsonb(data["value_jsonb"])

        if self._errors:
            return None

        return {
            "device_serial_id": data["device_serial_id"],
            "device_metric_id": data["device_metric_id"],
            "ts": ts,
            "value_jsonb": value_jsonb,
        }

    def _validate_ts(self, ts_raw: str) -> Optional[datetime.datetime]:
        ts_raw = ts_raw.strip()

        if not ts_raw:
            self._errors["ts"] = "ts must be a non-empty ISO-8601 datetime string."
            return None

        try:
            ts = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            self._errors["ts"] = "Invalid ISO-8601 datetime."
            return None

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)

        return ts.replace(microsecond=0)

    def _validate_value_jsonb(self, value_jsonb: dict) -> Optional[dict[str, Any]]:

        errors = {}

        for field, expected_type in self.VALUE_JSONB_REQUIRED_FIELDS.items():

            if field not in value_jsonb:
                errors[field] = f"{field} is required."
                continue

            value = value_jsonb[field]

            if not isinstance(value, expected_type):

                if isinstance(expected_type, tuple):
                    types = ", ".join(t.__name__ for t in expected_type)
                    errors[field] = f"{field} must be one of ({types})."

                else:
                    errors[field] = f"{field} must be {expected_type.__name__}."

        if errors:
            self._errors["value_jsonb"] = errors
            return None

        return {
            "t": value_jsonb["t"],
            "v": value_jsonb["v"],
        }
