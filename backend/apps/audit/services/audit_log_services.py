from dataclasses import dataclass, field
from uuid import UUID

from apps.audit.types import AuditLogCreateData
from apps.audit.models import AuditLog
from utils.dicts import normalize_schema

REQUIRED_FIELDS = {"audit_event_id", "entity_type", "entity_id", "event_type"}
OPTIONAL_FIELDS = {"actor_type", "actor_id", "severity", "occurred_at", "details"}
ALLOWED_ACTOR_TYPES = AuditLog.Actor.values
ALLOWED_SEVERITIES = AuditLog.Severity.values


@dataclass(slots=True)
class AuditLogCreateResult:
    attempted: int = 0
    created: int = 0
    errors: dict[int, dict[str, str]] = field(default_factory=dict)

    def add_error(self, i: int, field: str, message: str) -> None:
        self.errors.setdefault(i, {})[field] = message


def audit_log_create_batch(data: list[AuditLogCreateData]) -> AuditLogCreateResult:
    """
    Service function to bulk-insert AuditLog rows from a batch.

    - Deduplicates by audit_event_id within the batch.
    - Validates optional actor_type/severity against model choices.
    - Inserts via bulk_create(ignore_conflicts=True) for idempotency.
    """
    result = AuditLogCreateResult(attempted=len(data))
    if not data:
        return result

    # collect valid items
    to_create: list[AuditLog] = []
    seen: set[UUID] = set()

    for i, entry in enumerate(data):
        normalized, errors = normalize_schema(
            entry, required=REQUIRED_FIELDS, optional=OPTIONAL_FIELDS
        )
        if errors:
            result.errors[i] = errors
            continue

        # validate duplicates within the batch
        audit_event_id = normalized["audit_event_id"]
        if audit_event_id in seen:
            result.add_error(
                i,
                "audit_event_id",
                f"duplicate audit_event_id within batch: {audit_event_id}.",
            )
            continue
        seen.add(audit_event_id)

        if "actor_type" in normalized:
            actor_type = normalized["actor_type"].lower()
            if actor_type not in ALLOWED_ACTOR_TYPES:
                result.add_error(
                    i,
                    "actor_type",
                    f"actor_type must be one of: {ALLOWED_ACTOR_TYPES}.",
                )
                continue
            normalized["actor_type"] = actor_type

        if "severity" in normalized:
            severity = normalized["severity"].lower()
            if severity not in ALLOWED_SEVERITIES:
                result.add_error(i, "severity", f"severity must be one of: {ALLOWED_SEVERITIES}.")
                continue
            normalized["severity"] = severity

        to_create.append(AuditLog(**normalized))

    AuditLog.objects.bulk_create(to_create, ignore_conflicts=True)

    result.created = len(to_create)
    return result
