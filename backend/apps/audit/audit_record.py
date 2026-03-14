import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone
from enum import Enum


class AuditActorType(str, Enum):
    USER = 'user'
    SYSTEM = 'system'
    EXTERNAL = 'external'


@dataclass(frozen=True, slots=True)
class AuditActor:
    type: AuditActorType
    id: Optional[str] = None

    @staticmethod
    def user(user_id: Any) -> 'AuditActor':
        return AuditActor(type=AuditActorType.USER, id=str(user_id))

    @staticmethod
    def system(service_id: Optional[Any] = None) -> 'AuditActor':
        return AuditActor(type=AuditActorType.SYSTEM, id=service_id)

    @staticmethod
    def external(external_id: Optional[str] = None) -> 'AuditActor':
        return AuditActor(type=AuditActorType.EXTERNAL, id=external_id)


@dataclass(frozen=True, slots=True)
class AuditEntity:
    type: str  # 'RULE' | 'EVENT' | 'ACTION' | etc.
    id: str


class AuditSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """
    Audit message container used for producing audit events to Kafka.

    This class represents a single audit entry.
    It is intended to be created by domain services, and
    converted to a JSON-serializable payload with to_record().

    Usage example:
        record = AuditRecord(...)
        payload = record.to_record()
        audit_producer.produce(payload)
    """

    actor: AuditActor
    entity: AuditEntity

    event_type: str
    severity: AuditSeverity = AuditSeverity.INFO

    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)

    audit_event_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def to_record(self) -> dict[str, Any]:
        return {
            'actor_type': self.actor.type.value,
            'actor_id': self.actor.id,
            'entity_type': self.entity.type,
            'entity_id': self.entity.id,
            'event_type': self.event_type,
            'severity': self.severity.value,
            'occurred_at': self.occurred_at.isoformat(),
            'details': self.details,
            'audit_event_id': str(self.audit_event_id),
        }
