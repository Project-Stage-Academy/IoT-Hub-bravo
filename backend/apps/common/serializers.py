from typing import Any, Optional


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
        try:
            self._validated_data = self._validate(self.initial_data)
        except Exception as exc:
            self._validated_data = None
            self._errors["non_field_error"] = str(exc)
        return not self._errors

    def _validate(self, data: Any):
        raise NotImplementedError


class JSONSerializer(BaseSerializer):
    """
    Base serializer for JSON object payloads.

    Define:
        REQUIRED_FIELDS: dict[field_name, expected_type]
        OPTIONAL_FIELDS: dict[field_name, expected_type]

    Options:
        STRICT: if True, reject unknown fields.

    Override:
        _validate_fields(data)
    """

    REQUIRED_FIELDS: dict[str, type] = {}
    OPTIONAL_FIELDS: dict[str, type] = {}
    STRICT: bool = True

    def _validate(self, data: Any) -> Optional[dict[str, Any]]:
        if not isinstance(data, dict):
            self._errors['non_field_errors'] = 'Payload must be a JSON object.'
            return None

        self._validate_field_map(data, self.REQUIRED_FIELDS, required=True)
        self._validate_field_map(data, self.OPTIONAL_FIELDS, required=False)

        if self.STRICT:
            self._validate_no_unknown_fields(data)

        if self._errors:
            return None

        validated = self._validate_fields(data)
        if self._errors:
            return None

        return validated
    def _validate_field_map(
            self,
            data: dict[str, Any],
            fields: dict[str, type],
            *,
            required: bool,
    ) -> None:
        for field, expected_type in fields.items():
            if field not in data:
                if required:
                    self._errors[field] = f'{field} field is required.'
                continue

            value = data[field]

            if value is None and not required:
                continue

            if not isinstance(value, expected_type):
                self._errors[field] = f'{field} must be of type {expected_type.__name__}.'
                continue

    def _validate_no_unknown_fields(self, data: dict[str, Any]) -> None:
        allowed = set(self.REQUIRED_FIELDS) | set(self.OPTIONAL_FIELDS)
        unknown = set(data) - allowed
        if unknown:
            self._errors['non_field_errors'] = f'Unknown fields: {sorted(unknown)}'

    def _validate_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        return data