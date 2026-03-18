from enum import Enum
from typing import Any

from apps.audit.audit_record import (
    AuditEntity,
    AuditActor,
    AuditSeverity,
    AuditRecord,
)
from apps.rules.models import EventDelivery
from utils.normalization import to_iso8601_utc

ACTION_AUDIT_ENTITY = 'actions.Action'


class ActionAuditType(str, Enum):
    STARTED = 'actions.ACTION_STARTED'
    SUCCEEDED = 'actions.ACTION_SUCCEEDED'
    REJECTED = 'actions.ACTION_REJECTED'


def action_started(event_delivery: EventDelivery) -> AuditRecord:
    return AuditRecord(
        **_action_audit_base(event_delivery.pk),
        event_type=ActionAuditType.STARTED.value,
        severity=AuditSeverity.INFO,
        details={**_action_snapshot(event_delivery)},
    )


def action_succeeded(event_delivery: EventDelivery) -> AuditRecord:
    return AuditRecord(
        **_action_audit_base(event_delivery.pk),
        event_type=ActionAuditType.SUCCEEDED.value,
        severity=AuditSeverity.INFO,
        details={**_action_snapshot(event_delivery)},
    )


def action_rejected(event_delivery: EventDelivery) -> AuditRecord:
    return AuditRecord(
        **_action_audit_base(event_delivery.pk),
        event_type=ActionAuditType.REJECTED.value,
        severity=AuditSeverity.WARNING,
        details={**_action_snapshot(event_delivery)},
    )


def _action_entity(event_delivery_id: Any) -> AuditEntity:
    return AuditEntity(type=ACTION_AUDIT_ENTITY, id=str(event_delivery_id))


def _action_audit_base(event_delivery_id: Any) -> dict[str, Any]:
    return {
        'actor': AuditActor.system(),
        'entity': _action_entity(event_delivery_id),
    }


def _action_snapshot(event_delivery: EventDelivery) -> dict[str, Any]:
    return {
        'event_uuid': str(event_delivery.event_uuid),
        'rule_id': str(event_delivery.rule_id),
        'trigger_device_serial_id': str(event_delivery.trigger_device_serial_id),
        'delivery_type': event_delivery.delivery_type,
        'status': event_delivery.status,
        'attempts': event_delivery.attempts,
        'max_attempts': event_delivery.max_attempts,
        'last_attempt_at': to_iso8601_utc(event_delivery.last_attempt_at),
        'response_status': event_delivery.response_status,
        'error_message': event_delivery.error_message,
        'created_at': to_iso8601_utc(event_delivery.created_at),
        'updated_at': to_iso8601_utc(event_delivery.updated_at),
    }
