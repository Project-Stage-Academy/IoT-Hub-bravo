from typing import Any, Optional

from apps.common.serializers import BaseSerializer

ExpectedType = type | tuple[type, ...]


class JSONSerializer(BaseSerializer):
    """
    Base serializer for JSON object payloads.

    Define:
        REQUIRED_FIELDS: dict[field_name, expected_type]
        OPTIONAL_FIELDS: dict[field_name, expected_type]

    Options:
        STRICT_SCHEMA: if True, reject unknown fields.

    Override:
        _validate_fields(data)
    """

    REQUIRED_FIELDS: dict[str, ExpectedType] = {}
    OPTIONAL_FIELDS: dict[str, ExpectedType] = {}
    STRICT_SCHEMA: bool = True

    def _validate(self, data: Any) -> Optional[Any]:
        """
        Validate and normalize a JSON payload according to the serializer schema.

        Validation pipeline:
          1) Ensure the payload is a JSON object (dict).
          2) Validate required and optional fields:
             - Required fields must be present and match the expected type.
             - Optional fields, if present, must match the expected type.
          3) If STRICT_SCHEMA=True, reject any unknown fields that are
             not declared in REQUIRED_FIELDS or OPTIONAL_FIELDS.
          4) If the schema checks passed, call _validate_fields()

        Error handling:
          - Must not raise exceptions for validation errors.
          - Validation errors should be collected in self._errors.
          - If any errors are present, this method returns None and
            is_valid() will return False.

        Return value:
          - On success: returns a dict that becomes validated_data.
          - On failure: returns None.
        """
        if not isinstance(data, dict):
            self._errors['non_field_errors'] = 'Payload must be a JSON object.'
            return None

        self._validate_field_map(data, self.REQUIRED_FIELDS, required=True)
        self._validate_field_map(data, self.OPTIONAL_FIELDS, required=False)

        if self.STRICT_SCHEMA:
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
                self._errors[field] = f'{field} must be of type {self._type_name(expected_type)}.'
                continue

    @staticmethod
    def _type_name(t: ExpectedType) -> str:
        if isinstance(t, tuple):
            return ' or '.join(x.__name__ for x in t)
        return t.__name__

    def _validate_no_unknown_fields(self, data: dict[str, Any]) -> None:
        allowed = set(self.REQUIRED_FIELDS) | set(self.OPTIONAL_FIELDS)
        unknown = set(data) - allowed
        if unknown:
            self._errors['non_field_errors'] = f'Unknown fields: {sorted(unknown)}'

    def _validate_fields(self, data: dict[str, Any]) -> Any:
        """
        Custom validation and normalization after basic schema checks.

        This method is called only if:
          - the payload is a JSON object (dict),
          - required/optional fields exist and match declared types,
          - and (optionally) there are no unknown fields (STRICT_SCHEMA).

        You should override this method in child serializers to:
          - normalize values,
          - apply cross-field rules,
          - build the final output structure for the serializer.

        The returned dict becomes validated_data.

        Error handling:
          - Must not raise exceptions for validation errors.
          - Add error messages to self._errors and return
            any dict (it will be ignored if errors are present).
          - If self._errors is non-empty after this method returns,
            is_valid() will return False.
        """
        return data
