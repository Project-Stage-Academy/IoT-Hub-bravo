from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from apps.common.serializers import BaseSerializer
import uuid

# =========================
# Input serializer (GET list)
# =========================


@dataclass(slots=True)
class EventListQuery:
    rule_id: Optional[int] = None
    device_serial_id: Optional[str] = None
    severity: Optional[str] = None  # reserved for future
    acknowledged: Optional[bool] = None
    limit: int = 50
    offset: int = 0


class EventListQuerySerializer(BaseSerializer):
    """
    Validates query params for GET /api/events/

    Query params (all optional):
    - rule_id: int
    - device_serial_id: str  (filter by trigger device serial ID)
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
        device_serial_id = self._parse_optional_string(
            data.get("device_serial_id"),
            field="device_serial_id",
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
            device_serial_id=device_serial_id,
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
            "event_uuid": str(event.event_uuid),
            "rule_triggered_at": event.rule_triggered_at.isoformat(),
            "created_at": event.created_at.isoformat(),
            "acknowledged": event.acknowledged,
            "rule": {
                "id": event.rule_id,
                "name": event.rule.name if event.rule else None,
            },
            "trigger_device_serial_id": event.trigger_device_serial_id,
            "trigger_context": event.trigger_context,
        }


class EventDetailSerializer:
    """
    Serializes Event for detail endpoint.
    """

    @staticmethod
    def to_dict(event) -> dict[str, Any]:
        return {
            "event_uuid": str(event.event_uuid),
            "rule_triggered_at": event.rule_triggered_at.isoformat(),
            "created_at": event.created_at.isoformat(),
            "acknowledged": event.acknowledged,
            "rule": {
                "id": event.rule_id,
                "name": event.rule.name if event.rule else None,
            },
            "trigger_device_serial_id": event.trigger_device_serial_id,
            "trigger_context": event.trigger_context,
        }

from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

from apps.common.serializers import BaseSerializer


@dataclass(slots=True)
class ExternalEventRequest:
    source: str
    external_event_id: str
    device_external_id: str
    timestamp: datetime
    payload: Dict[str, Any]


class ExternalEventRequestSerializer(BaseSerializer):
    """
    Validates payload for POST /api/events/external/
    
    Expected JSON format:

    {
      "source": "softserve-office",
      "external_event_id": "evt-123",
      "device_external_id": "SERIAL-123",
      "timestamp": "2026-03-16T15:06:59Z",
      "payload": {
        "rule_id": 12,
        "metric": "humidity",
        "value": 150,
        "threshold": 50,
        "telemetry_ts": "2026-03-16T20:55:00Z",
        "notification": {
          "channel": "discord",
          "message": "Critical temperature alert!",
          "webhook": "https://webhook.site/..."
        }
      }
    }
    """

    def __init__(self, data: Any):
        super().__init__(data)
        self._validated_data: Optional[ExternalEventRequest] = None

    def _validate(self, data: Any) -> Optional[ExternalEventRequest]:
        if not isinstance(data, dict):
            self._errors["body"] = "Payload must be a JSON object."
            return None

        # required top-level fields
        source = self._parse_required_string(data.get("source"), "source")
        external_event_id = self._parse_required_string(data.get("external_event_id"), "external_event_id")
        device_external_id = self._parse_required_string(data.get("device_external_id"), "device_external_id")
        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                self._errors["timestamp"] = "timestamp must be a valid ISO 8601 string."
        else:
            self._errors["timestamp"] = "timestamp is required."

        # payload validation
        payload = data.get("payload")
        if not isinstance(payload, dict):
            self._errors["payload"] = "payload must be a JSON object."
        else:
            # rule_id is required inside payload
            rule_id = payload.get("rule_id")
            if not isinstance(rule_id, int) or rule_id <= 0:
                self._errors["payload.rule_id"] = "rule_id is required and must be a positive integer."

            # optional notification
            notification = payload.get("notification")
            if notification is not None and not isinstance(notification, dict):
                self._errors["payload.notification"] = "notification must be an object if provided."

        if self._errors:
            return None

        return ExternalEventRequest(
            source=source,
            external_event_id=external_event_id,
            device_external_id=device_external_id,
            timestamp=timestamp,
            payload=payload
        )

    def _parse_required_string(self, value: Any, field: str) -> Optional[str]:
        if not value or not isinstance(value, str):
            self._errors[field] = f"{field} is required and must be a string."
            return None
        return value.strip()
    import uuid

def map_external_to_internal(validated: ExternalEventRequest) -> dict:
    payload = validated.payload
    notification = payload.get("notification", {})

    return {
        "event_uuid": str(uuid.uuid4()),
        "rule_triggered_at": validated.timestamp.isoformat(),
        "rule_id": payload.get("rule_id"),
        "trigger_device_serial_id": validated.device_external_id,
        "trigger_context": {
            "metric_type": payload.get("metric"),
            "value": payload.get("value"),
            "telemetry_timestamp": payload.get("telemetry_ts"),
        },
        "action": {
            "webhook": {
                "url": notification.get("webhook"),
                "enabled": bool(notification.get("webhook")),
            },
            "notification": {
                "channel": notification.get("channel"),
                "enabled": bool(notification),
                "message": notification.get("message"),
            },
        },
    }
