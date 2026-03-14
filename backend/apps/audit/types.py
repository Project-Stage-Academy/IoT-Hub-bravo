from typing import TypedDict, Any
import uuid
import datetime


class AuditLogCreateData(TypedDict, total=False):
    """
    DB insert payload shape for AuditLog creation.
    Required keys are enforced by validation/service logic.
    Optional keys may be omitted to use DB defaults.
    """

    # required by contract
    audit_event_id: uuid.UUID
    entity_type: str
    entity_id: str
    event_type: str

    # optional
    actor_type: str
    actor_id: str
    severity: str
    occurred_at: datetime.datetime
    details: dict[str, Any]
