from .base_device_serializer import BaseDeviceSerializer


class DeviceUpdateV1Serializer(BaseDeviceSerializer):
    required_fields = ()

    FIELD_TYPES = {
        "name": str,
        "description": (str, type(None)),
        "is_active": bool,
    }

    def to_canonical(self):
        return {
            "name": self.validated_data.get("name"),
            "description": self.validated_data.get("description"),
            "is_active": self.validated_data.get("is_active"),
        }
