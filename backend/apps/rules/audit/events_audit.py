from enum import Enum
from typing import Any

from apps.audit.audit_record import (
    AuditEntity,
    AuditActor,
    AuditSeverity,
    AuditRecord,
)
from apps.rules.models import Event
from utils.normalization import to_iso8601_utc

EVENT_AUDIT_ENTITY = 'events.Event'


class EventAuditType(str, Enum):
    CREATED = 'events.EVENT_CREATED'
    ACKNOWLEDGED = 'events.EVENT_ACKNOWLEDGED'


def event_created(event: Event) -> AuditRecord:
    return AuditRecord(
        entity=_event_entity(event.pk),
        actor=AuditActor.system(),
        event_type=EventAuditType.CREATED.value,
        severity=AuditSeverity.INFO,
        details={'after': _event_snapshot(event)},
    )


def event_acknowledged(user_id: Any, event_id: Any) -> AuditRecord:
    return AuditRecord(
        entity=_event_entity(event_id),
        actor=AuditActor.user(user_id),
        event_type=EventAuditType.ACKNOWLEDGED.value,
        severity=AuditSeverity.INFO,
        details={
            'before': {'acknowledged': False},
            'after': {'acknowledged': True},
        },
    )


def _event_entity(event_id: Any) -> AuditEntity:
    return AuditEntity(type=EVENT_AUDIT_ENTITY, id=str(event_id))


def _event_snapshot(event: Event) -> dict[str, Any]:
    return {
        'event_uuid': str(event.event_uuid),
        'rule_triggered_at': to_iso8601_utc(event.rule_triggered_at),
        'rule_id': str(event.rule),
        'acknowledged': event.acknowledged,
        'created_at': to_iso8601_utc(event.created_at),
        'trigger_device_serial_id': str(event.trigger_device_serial_id),
    }
