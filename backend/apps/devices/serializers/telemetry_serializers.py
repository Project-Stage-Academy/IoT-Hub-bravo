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
