from typing import Any
import logging

from django.core.exceptions import ValidationError

from apps.common.serializers import BaseSerializer
from apps.rules.utils.serializers_utils import validate_field

logger = logging.getLogger(__name__)


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
        'device_metric_id': int,
    }

    REQUIRED_FIELDS = {
        'schema_version': int,
        'name': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric_id': int,
    }

    def _validate(self, data: Any):
        if not isinstance(data, dict):
            raise ValidationError("Payload must be a JSON object")

        validated = {}

        for field, expected_type in self.REQUIRED_FIELDS.items():
            value, field_errors = validate_field(
                self.initial_data, field, expected_type, required=True
            )
            if field_errors:
                self._errors.update(field_errors)
            else:
                validated[field] = value

        optional_fields = set(self.FIELDS_TYPE_MAP.keys()) - set(self.REQUIRED_FIELDS.keys())
        for field in optional_fields:
            expected_type = self.FIELDS_TYPE_MAP[field]
            value, field_errors = validate_field(
                self.initial_data, field, expected_type, required=False
            )
            if field_errors:
                self._errors.update(field_errors)
            else:
                validated[field] = value

        if self._errors:
            return None

        return validated


class RulePatchSerializer(BaseSerializer):
    """Serilizer for patch"""

    FIELDS_TYPE_MAP = {
        'schema_version': int,
        'name': str,
        'description': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric_id': int,
    }

    def _validate(self, data: Any):
        if not isinstance(data, dict):
            raise ValidationError("Payload must be a JSON object")

        validated = {}

        for field, expected_type in self.FIELDS_TYPE_MAP.items():
            if field in data:
                value, field_errors = validate_field(
                    self.initial_data, field, expected_type, required=False
                )
                if field_errors:
                    self._errors.update(field_errors)
                else:
                    validated[field] = value

        if self._errors:
            return None

        if not validated:
            raise ValidationError("At least one field must be provided")

        return validated
