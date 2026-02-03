from django.db import IntegrityError, DatabaseError
from ..models import Device


class DeviceService:
    @staticmethod
    def create_device(
        *,
        serial_id: str,
        name: str,
        user_id: int,
        description: str | None = None,
        is_active: bool = False,
    ) -> Device:
        try:
            return Device.objects.create(
                serial_id=serial_id,
                name=name,
                description=description,
                user_id=user_id,
                is_active=is_active,
            )

        except IntegrityError as e:
            raise RuntimeError("Device with the same serial_id already exists")
        except DatabaseError as e:
            raise RuntimeError("Database error occurred while creating device")

    @staticmethod
    def update_device(
        *,
        instance: Device,
        serial_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        user_id: int | None = None,
    ) -> Device:
        if serial_id is not None:
            instance.serial_id = serial_id

        if name is not None:
            instance.name = name

        if description is not None:
            instance.description = description

        if is_active is not None:
            instance.is_active = is_active

        if user_id is not None:
            instance.user_id = user_id
        try:
            instance.save()
            return instance

        except IntegrityError as e:
            raise RuntimeError("Device update violates a data constraint")

        except DatabaseError as e:
            raise RuntimeError("Database error occurred while updating device")

    @staticmethod
    def delete_device(device: Device) -> None:
        try:
            device.delete()

        except DatabaseError as e:
            raise RuntimeError("Database error occurred while deleting device")
