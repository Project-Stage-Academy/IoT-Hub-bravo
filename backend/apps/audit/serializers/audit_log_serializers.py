import datetime
import uuid
from typing import Any, Optional

from apps.audit.types import AuditLogCreateData
from apps.common.serializers import JSONSerializer, BaseSerializer
from utils.normalization import normalize_str, parse_iso8601_utc
from utils.json import is_json_serializable


class AuditLogSerializer(JSONSerializer):
    REQUIRED_FIELDS = {
        'audit_event_id': str,
        'entity_type': str,
        'entity_id': (str, int),
        'event_type': str,
    }
    OPTIONAL_FIELDS = {
        'actor_type': str,
        'actor_id': (str, int),
        'severity': str,
        'occurred_at': str,
        'details': dict,
    }

    def _validate_fields(self, data: dict[str, Any]) -> AuditLogCreateData:
        validated = {
            'audit_event_id': self._validate_audit_event_id(data.get('audit_event_id')),
            'entity_type': normalize_str(data.get('entity_type')),
            'entity_id': self._normalize_id(data.get('entity_id')),
            'event_type': normalize_str(data.get('event_type')),
            'actor_type': normalize_str(data.get('actor_type', '')),
            'actor_id': self._normalize_id(data.get('actor_id')),
            'severity': normalize_str(data.get('severity', '')),
            'occurred_at': self._validate_occurred_at(data.get('occurred_at')),
            'details': self._validate_details(data.get('details')),
        }

        for field, field_type in self.REQUIRED_FIELDS.items():
            if validated[field] is None:
                self._errors[field] = f'{field} must be a non-empty value.'

        # return clean dict with omitted optional Nones
        return {k: v for k, v in validated.items() if v is not None}

    @staticmethod
    def _normalize_id(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            s = value.strip()
            return s or None
        return None

    def _validate_audit_event_id(self, audit_event_id_raw: str) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(normalize_str(audit_event_id_raw))
        except (ValueError, TypeError):
            self._errors['audit_event_id'] = 'audit_event_id must be a valid UUID.'
            return None

    def _validate_occurred_at(self, occurred_at_raw: Optional[str]) -> Optional[datetime.datetime]:
        if occurred_at_raw is None:
            return None

        occurred_at = parse_iso8601_utc(occurred_at_raw)
        if occurred_at is None:
            self._errors['occurred_at'] = 'occurred_at must be a valid ISO-8601 datetime.'
            return None

        return occurred_at

    def _validate_details(self, details_raw: Optional[dict]) -> Optional[dict[str, Any]]:
        if details_raw is None:
            return None

        details: dict[str, Any] = {}
        errors: dict[str, Any] = {}

        for key, value in details_raw.items():
            if not isinstance(key, str) or not key.strip():
                errors[str(key)] = 'details key name must be a non-empty string.'
                continue

            key_norm = normalize_str(key)

            if not is_json_serializable(value):
                errors[key_norm] = 'details value must be JSON-serializable.'
                continue

            details[key_norm] = value

        if errors:
            self._errors['details'] = errors
            return None

        return details


class AuditLogBatchSerializer(BaseSerializer):
    def __init__(self, data: Any):
        super().__init__(data)
        self._valid_items: list[AuditLogCreateData] = []
        self._item_errors: dict[int, Any] = {}

    @property
    def valid_items(self) -> list[AuditLogCreateData]:
        return self._valid_items

    @property
    def item_errors(self) -> dict[int, Any]:
        return self._item_errors

    def _validate(self, data: Any) -> Optional[list[AuditLogCreateData]]:
        if not isinstance(data, list):
            self._errors['non_field_errors'] = 'Payload must be a JSON array.'
            return None

        if not data:
            self._errors['items'] = {'non_field_errors': 'Empty batch.'}
            return None

        for index, item in enumerate(data):
            s = AuditLogSerializer(item)
            if s.is_valid():
                self._valid_items.append(s.validated_data)
            else:
                self._item_errors[index] = s.errors

        if self._item_errors:
            self._errors['items'] = self._item_errors
            return None

        return self._valid_items
