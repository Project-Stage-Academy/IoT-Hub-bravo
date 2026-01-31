# serializers/device_serializer.py
from typing import Any, Dict
from ..models import Device

class DeviceSerializer:
    def __init__(self, instance: Device | None = None, data: Dict[str, Any] | None = None, partial: bool = False):
        self.instance = instance
        self.initial_data = data
        self.partial = partial
        self._validated_data = None
        self._errors = None

    def is_valid(self) -> bool:
        self._errors = {}
        self._validated_data = {}

        if not isinstance(self.initial_data, dict):
            self._errors["non_field_errors"] = "Invalid data format"
            return False

        required_fields = ["serial_id", "name", "user_id"]
        if not self.partial:
            for field in required_fields:
                if field not in self.initial_data or self.initial_data[field] in ("", None):
                    self._errors[field] = "This field is required."

        for field, expected_type in [
            ("serial_id", str),
            ("name", str),
            ("description", (str, type(None))),
            ("user_id", int),
            ("is_active", bool),
        ]:
            if field in self.initial_data:
                value = self.initial_data[field]
                if not isinstance(value, expected_type):
                    self._errors[field] = f"Must be {expected_type}."
                else:
                    self._validated_data[field] = value.strip() if isinstance(value, str) else value

        return not bool(self._errors)

    @property
    def validated_data(self) -> Dict[str, Any]:
        if self._validated_data is None:
            raise RuntimeError("Call `.is_valid()` before accessing `.validated_data`")
        return self._validated_data

    @property
    def errors(self) -> Dict[str, Any]:
        return self._errors or {}

    def to_representation(self, instance: Device) -> Dict[str, Any]:
        return {
            "id": instance.id,
            "serial_id": instance.serial_id,
            "name": instance.name,
            "description": instance.description,
            "user_id": instance.user.id,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }
