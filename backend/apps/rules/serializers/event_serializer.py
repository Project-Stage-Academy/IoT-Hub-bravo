from dataclasses import dataclass
from typing import Any, Optional


# =========================
# Base serializer
# =========================

class BaseSerializer:
    """
    Minimal serializer for plain Django.

    Purpose:
    - validate input data (query params / JSON)
    - store errors
    - expose validated_data only after is_valid()
    """

    def __init__(self, data: Any):
        self.initial_data = data
        self._validated_data: Any = None
        self._errors: dict[str, Any] = {}

    @property
    def validated_data(self):
        if self._validated_data is None:
            raise ValueError("Call is_valid() before accessing validated_data.")
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


# =========================
# Input serializer (GET list)
# =========================

@dataclass(slots=True)
class EventListQuery:
    rule_id: Optional[int] = None
    device_id: Optional[int] = None
    severity: Optional[str] = None  # reserved for future
    acknowledged: Optional[bool] = None
    limit: int = 50
    offset: int = 0


class EventListQuerySerializer(BaseSerializer):
    """
    Validates query params for GET /api/events/

    Query params (all optional):
    - rule_id: int
    - device_id: int  (will be applied via trigger telemetry later)
    - severity: str   (not supported by model yet, reserved)
    - acknowledged: bool
    - limit: int
    - offset: int
    """

    DEFAULT_LIMIT = 50
    MAX_LIMIT = 200

    def __init__(self, data: Any):
        super().__init__(data)
        self._validated_data: Optional[EventListQuery] = None

    def _validate(self, data: Any) -> Optional[EventListQuery]:
        if not isinstance(data, dict):
            self._errors["query"] = "Query params must be an object."
            return None

        rule_id = self._parse_optional_positive_int(data.get("rule_id"), field="rule_id")
        device_id = self._parse_optional_positive_int(
            data.get("device_id"),
            field="device_id",
        )

        acknowledged = self._parse_optional_bool(
            data.get("acknowledged"),
            field="acknowledged",
        )

        limit = self._parse_optional_positive_int(data.get("limit"), field="limit")
        offset = self._parse_optional_non_negative_int(data.get("offset"), field="offset")

        severity = self._parse_optional_string(data.get("severity"), field="severity")

        if limit is None:
            limit = self.DEFAULT_LIMIT
        if offset is None:
            offset = 0

        if limit > self.MAX_LIMIT:
            self._errors["limit"] = f"limit must be <= {self.MAX_LIMIT}."

        if self._errors:
            return None

        return EventListQuery(
            rule_id=rule_id,
            device_id=device_id,
            severity=severity,
            acknowledged=acknowledged,
            limit=limit,
            offset=offset,
        )

    def _parse_optional_positive_int(self, raw: Any, *, field: str) -> Optional[int]:
        if raw is None or raw == "":
            return None

        try:
            value = int(raw)
        except (TypeError, ValueError):
            self._errors[field] = f"{field} must be an integer."
            return None

        if value <= 0:
            self._errors[field] = f"{field} must be > 0."
            return None

        return value

    def _parse_optional_non_negative_int(self, raw: Any, *, field: str) -> Optional[int]:
        if raw is None or raw == "":
            return None

        try:
            value = int(raw)
        except (TypeError, ValueError):
            self._errors[field] = f"{field} must be an integer."
            return None

        if value < 0:
            self._errors[field] = f"{field} must be >= 0."
            return None

        return value

    def _parse_optional_bool(self, raw: Any, *, field: str) -> Optional[bool]:
        if raw is None or raw == "":
            return None

        if isinstance(raw, bool):
            return raw

        if not isinstance(raw, str):
            self._errors[field] = f"{field} must be true/false."
            return None

        normalized = raw.strip().lower()

        if normalized in ("true", "1", "yes"):
            return True
        if normalized in ("false", "0", "no"):
            return False

        self._errors[field] = f"{field} must be true/false."
        return None

    def _parse_optional_string(self, raw: Any, *, field: str) -> Optional[str]:
        if raw is None or raw == "":
            return None

        if not isinstance(raw, str):
            self._errors[field] = f"{field} must be a string."
            return None

        value = raw.strip()
        return value or None


# =========================
# Output serializers
# =========================

class EventListItemSerializer:
    """
    Serializes Event for list endpoint.
    Must stay lightweight (no DB queries inside).
    """

    @staticmethod
    def to_dict(event) -> dict[str, Any]:
        return {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "created_at": event.created_at.isoformat(),
            "acknowledged": event.acknowledged,
            "rule": {
                "id": event.rule_id,
                "name": event.rule.name if event.rule else None,
            },
            "trigger_telemetry_id": event.trigger_telemetry_id,
            "trigger_device_id": event.trigger_device_id,
        }


class EventDetailSerializer:
    """ 
    Serializes Event for detail endpoint. 
    """

    @staticmethod
    def to_dict(event) -> dict[str, Any]:
        return {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "created_at": event.created_at.isoformat(),
            "acknowledged": event.acknowledged,
            "rule": {
                "id": event.rule_id,
                "name": event.rule.name if event.rule else None,
            },
            "trigger_telemetry_id": event.trigger_telemetry_id,
            "trigger_device_id": event.trigger_device_id,
        }
