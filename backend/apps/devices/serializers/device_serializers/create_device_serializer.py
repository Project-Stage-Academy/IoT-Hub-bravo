from .base_device_serializer import BaseDeviceSerializer


class DeviceCreateV1Serializer(BaseDeviceSerializer):
    required_fields = ("serial_id", "name", "user_id")
    FIELD_TYPES = {
        "serial_id": str,
        "name": str,
        "description": (str, type(None)),
        "user_id": int,
        "is_active": bool,
    }

    def to_canonical(self):
        return {
            "serial_id": self.validated_data["serial_id"],
            "name": self.validated_data["name"],
            "description": self.validated_data.get("description"),
            "user_id": self.validated_data["user_id"],
            "is_active": self.validated_data.get("is_active", False),
        }
