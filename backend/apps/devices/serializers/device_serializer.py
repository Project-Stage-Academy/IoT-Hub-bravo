from typing import Any, Dict
from ..models import Device


class DeviceSerializer:
    def __init__(self, instance: Device | None = None, data: Dict[str, Any] | None = None, partial: bool = False,):
        self.instance = instance
        self.initial_data = data
        self.partial = partial
        self._validated_data = None
        self._errors = None

    def is_valid(self) -> bool:
     self._errors = {}
     self._validated_data = {}

    # checking if initial data is an instance of the dict
     if not isinstance(self.initial_data, dict):
        self._errors["non_field_errors"] = "Invalid data format"
        return False
     required_fields = ["serial_id", "name", "user_id"]

    # check for required fields (ignored if partial = True) 
     if not self.partial:
         for field in required_fields:
             if field not in self.initial_data or self.initial_data[field] in ("", None):
                 self._errors[field] = "This field is required."

     if self._errors:
         return False

    # validate fields: serial_id, name, description and user_id
     if "serial_id" in self.initial_data:
         value = self.initial_data["serial_id"]
         if not isinstance(value, str):
             self._errors["serial_id"] = "Must be a string."
         else:
             self._validated_data["serial_id"] = value.strip()

     if "name" in self.initial_data:
         value = self.initial_data["name"]
         if not isinstance(value, str):
             self._errors["name"] = "Must be a string."
         else:
             self._validated_data["name"] = value.strip()

     if "description" in self.initial_data:
         value = self.initial_data["description"]
         if value is not None and not isinstance(value, str):
             self._errors["description"] = "Must be a string."
         else:
             self._validated_data["description"] = value

     if "user_id" in self.initial_data:
         value = self.initial_data["user_id"]
         if not isinstance(value, int):
             self._errors["user_id"] = "Must be an integer."
         else:
             self._validated_data["user_id"] = value
             
     if "is_active" in self.initial_data:
        value = self.initial_data["is_active"]
        if not isinstance(value, bool):
            self._errors["is_active"] = "Must be a boolean."
        else:
            self._validated_data["is_active"] = value

     return not bool(self._errors)

    @property
    def validated_data(self) -> Dict[str, Any]:
        if self._validated_data is None:
            raise RuntimeError(
                "You must call `.is_valid()` before accessing `.validated_data`"
            )
        return self._validated_data

    @property
    def errors(self) -> Dict[str, Any]:
        return self._errors or {}

    def create(self) -> Device:
        if self._validated_data is None:
            raise RuntimeError("Call is_valid() before create()")
        try:
            device = Device.objects.create(**self._validated_data)
            self.instance = device
            return device
        except Exception:
            raise RuntimeError("Creation failed!")

    def update(self, instance: Device) -> Device:
        if self._validated_data is None:
            raise RuntimeError("Call is_valid() before update()")
        try:
            # instance.serial_id = self._validated_data.get("serial_id", instance.serial_id)
            # instance.name = self._validated_data.get("name", instance.name)
            # instance.description = self._validated_data.get("description", instance.description)
            # instance.is_active = self._validated_data.get("is_active", instance.is_active)
            for field, value in self._validated_data.items():
                setattr(instance, field, value)
            instance.save()
            return instance
        except:
            raise RuntimeError("Update failed!")

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
