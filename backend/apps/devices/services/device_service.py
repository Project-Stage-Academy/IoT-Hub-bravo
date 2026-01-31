from typing import Any, Dict
from ..models import Device


class DeviceService:
    @staticmethod
    def create_device(validated_data: dict) -> Device:
        try:
            device = Device.objects.create(**validated_data)
            return device
        except Exception as e:
            raise RuntimeError(f"Device creation failed: {str(e)}")

    @staticmethod
    def update_device(instance: Device, validated_data: dict) -> Device:
        try:
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            return instance
        except Exception as e:
            raise RuntimeError(f"Device update failed: {str(e)}")


    @staticmethod
    def delete_device(device: Device) -> None:
        try:
            device.delete()
        except Exception as e:
            raise RuntimeError(f"Delete failed: {e}")
