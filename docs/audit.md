# Audit Logging

## Purpose
Audit logging provides a persistent trail of important system activity (e.g. rule changes, evaluations, deliveries/actions) so operators can trace system behavior for debugging and compliance.

The audit pipeline is designed to be:
- **Structured**: audit records have a consistent schema (not free-form logs).
- **Idempotent**: duplicates are safe (Kafka at-least-once delivery, retries).
- **Searchable**: records can be filtered by entity/event/actor/severity and time.

---

## Core concepts

### AuditLog (DB storage)
Audit records are persisted in the `audit_logs` table via the `AuditLog` model.

Key fields:
- `audit_event_id` — UUID idempotency key (**unique**). Prevents duplicates.
- `entity_type`, `entity_id` — what the record is about (e.g. `rules.Rule`, id `42`).
- `event_type` — what happened (namespaced string, e.g. `rules.RULE_UPDATED`).
- `actor_type`, `actor_id` — who initiated it (`user`, `system`, `external`).
- `severity` — `info` / `warning` / `error`.
- `occurred_at` — event timestamp.
- `details` — structured JSON metadata (must be JSON-serializable).

### AuditRecord (producer-side contract)
When services want to publish an audit event, they should build an `AuditRecord` (dataclass).  
`AuditRecord.to_record()` converts it into a JSON-serializable dictionary suitable for transport.

Important:
- `AuditRecord` is a **producer-side** contract.
- `details` must be JSON-serializable (no raw `datetime`, `Decimal`, ORM objects, etc. unless they are converted).

---

## Data flow

### Producer → Kafka
1. A domain/service layer creates an `AuditRecord`.
2. The record is converted using `to_record()` and published to the audit topic.

### Consumer → DB
1. Kafka consumer reads messages.
2. Each message is validated/normalized by:
   - `AuditLogSerializer` (single)
   - `AuditLogBatchSerializer` (batch)
3. Valid items are persisted with `audit_log_create_batch()` using bulk insert and idempotency rules.

---

## Idempotency guarantees

Duplicates are handled using:
- `audit_event_id` (unique constraint)
- `bulk_create(ignore_conflicts=True)`

---

## Guidelines for details

`details` should be:
- structured: key-value dictionary with predictable keys 
- bounded: avoid big payloads
- safe: do not store secrets/credentials

Avoid:
- ORM objects 
- raw datetime/Decimal unless converted to string 
- large nested blobs

---

## Audit publishing

### 1) Define event types
Use a namespaced string format to avoid collisions across modules/services:

**Recommended format**
- `<namespace>.<EVENT_NAME>`, e.g.:
  - `rules.RULE_CREATED`
  - `rules.RULE_UPDATED`
  - `rules.RULE_EVALUATED`
  - `actions.ACTION_STARTED`
  - `actions.ACTION_SUCCEEDED`
  - `actions.ACTION_REJECTED`

Keep naming consistent across the codebase.

### 2) Add an audit builder module for the domain
Create a builder module near the domain logic (example: `apps/rules/audit.py`).
It should:
- define `Enum` of event types for that domain
- provide helper functions that return `AuditRecord`

Example:

```python
from enum import Enum
from apps.audit.audit_record import AuditActor, AuditEntity, AuditRecord, AuditSeverity

RULE_ENTITY = 'rules.Rule'

class RuleAuditType(str, Enum):
    UPDATED = 'rules.RULE_UPDATED'

def rule_updated(rule_id: int, actor_user_id: int, details: dict) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.user(actor_user_id),
        entity=AuditEntity(type=RULE_ENTITY, id=str(rule_id)),
        event_type=RuleAuditType.UPDATED.value,
        severity=AuditSeverity.INFO,
        details=details,
    )
```

### 3) Call `publish_audit_event()` from the application flow

Emit audit events from real execution paths

Example:
```python
from apps.audit.publisher import publish_audit_event
from apps.rules.audit.rules_audit import rule_updated

...
publish_audit_event(event=rule_updated(rule_id=42, actor_user_id=55, details={...}))
...
```
