from typing import Optional, Any
import logging


logger = logging.getLogger(__name__)


class BaseSerializer:
    def __init__(self, data: Any):
        self.initial_data = data
        self._validated_data: Optional[Any] = None
        self._errors: dict[str, Any] = {}

    @property
    def validated_data(self):
        if self._validated_data is None:
            raise ValueError('Call is_valid() before accessing validated_data.')
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
    

class RuleCreateSerializer(BaseSerializer):
    """
    Docstring for RuleCreateSerializer
    """

    SCHEMA_VERSION = 1
    FIELDS_TYPE_MAP = {
        'schema_version': int,
        'name': str,
        'description': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric': int,
    }
    
    REQUIRED_FIELDS = {
        'schema_version': int,
        'name': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric': int,
    }

    def _validate(self, data: Any):
        if not isinstance(data, dict):
            self._errors['non_field_error'] = "Payload must be a JSON object."
            return None

        validated = {}

        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in data:
                self._errors[field] = "This field is required."
            elif not isinstance(data[field], expected_type):
                self._errors[field] = f"{field} must be of type {expected_type.__name__}."
            else:
                validated[field] = data[field]

        optional_fields = set(self.FIELDS_TYPE_MAP.keys()) - set(self.REQUIRED_FIELDS.keys())
        for field in optional_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, self.FIELDS_TYPE_MAP[field]):
                    self._errors[field] = f"{field} must be of type {self.FIELDS_TYPE_MAP[field].__name__}."
                else:
                    validated[field] = value
            else:
                validated[field] = "" if field == "description" else None

        if self._errors:
            return None

        return validated
        