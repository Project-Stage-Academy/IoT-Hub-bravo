import datetime
from typing import Optional, Any

from apps.common.serializers import BaseSerializer, JSONSerializer
from utils.normalization import parse_iso8601_utc, normalize_str


class TelemetryCreateSerializer(JSONSerializer):
    SCHEMA_VERSION = 1
    METRIC_VALUE_TYPES = (bool, int, float, str)

    REQUIRED_FIELDS = {
        "schema_version": int,
        "device": str,
        "metrics": dict,
        "ts": str,
    }

    def _validate_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self._schema_version_valid(data["schema_version"]):
            return {}

        return {
            "device_serial_id": self._validate_device(data["device"]),
            "metrics": self._validate_metrics(data["metrics"]),
            "ts": self._validate_ts(data["ts"]),
        }

    def _schema_version_valid(self, schema_version: int) -> bool:
        if schema_version != self.SCHEMA_VERSION:
            self._errors["schema_version"] = (
                f"Unsupported schema_version: {schema_version}. "
                f"Supported: {self.SCHEMA_VERSION}."
            )
            return False
        return True

    def _validate_device(self, device_raw: str) -> Optional[str]:
        device_raw = normalize_str(device_raw)
        if not device_raw:
            self._errors["device"] = "device must be a non-empty string."
        return device_raw

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
        ts = parse_iso8601_utc(ts_raw)

        if ts is None:
            self._errors["ts"] = "ts must be a valid ISO-8601 datetime."
            return None

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
