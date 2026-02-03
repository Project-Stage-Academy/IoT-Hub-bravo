# serializers/device_serializer.py
from typing import Any, Dict
from ...models import Device


class BaseDeviceSerializer:
    required_fields = ()
    FIELD_TYPES = {}

    def __init__(self, data: Dict[str, Any] | None = None, partial: bool = False):
        self.initial_data = data or {}
        self.partial = partial
        self._validated_data: Dict[str, Any] | None = None
        self._errors: Dict[str, str] | None = None

    def validate_type(self, field: str, value: Any, expected_type: Any) -> bool:
        if not isinstance(value, expected_type):
            self._errors[field] = f"'{field}' must be a valid value."
            return False
        return True

    def is_valid(self) -> bool:
        self._errors = {}
        self._validated_data = {}

        if not isinstance(self.initial_data, dict):
            self._errors["non_field_errors"] = "Invalid data format"
            return False

        if not self.partial:
            for field in self.required_fields:
                if field not in self.initial_data or self.initial_data[field] in ("", None):
                    self._errors[field] = "This field is required."

        if self._errors:
            return False

        for field, expected_type in self.FIELD_TYPES.items():
            if field in self.initial_data:
                value = self.initial_data[field]
                if self.validate_type(field, value, expected_type):
                    if isinstance(value, str) and value is not None:
                        self._validated_data[field] = value.strip()
                    else:
                        self._validated_data[field] = value

        return not bool(self._errors)

    @property
    def validated_data(self) -> Dict[str, Any]:
        if self._validated_data is None:
            raise RuntimeError("Call `.is_valid()` before accessing `.validated_data`")
        return self._validated_data

    @property
    def errors(self) -> Dict[str, Any]:
        return self._errors or {}


class DeviceOutputSerializer:
    @staticmethod
    def to_representation(
        instance: Device, fields: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        data = {}

        default_fields = [
            "id",
            "serial_id",
            "name",
            "description",
            "user_id",
            "is_active",
            "created_at",
        ]
        fields = fields or default_fields

        for field in fields:
            try:
                if field == "user_id":
                    data[field] = getattr(instance.user, "id", None)
                else:
                    value = getattr(instance, field, None)
                    if isinstance(value, (int, str, bool)):
                        data[field] = value
                    elif hasattr(value, "isoformat"):
                        data[field] = value.isoformat()
                    else:
                        data[field] = value
            except Exception:
                data[field] = None
        return data
