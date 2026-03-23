from enum import Enum
from typing import Any

from apps.audit.audit_record import (
    AuditEntity,
    AuditActor,
    AuditSeverity,
    AuditRecord,
)
from apps.rules.models import Rule
from utils.dicts import diff_dicts

RULE_AUDIT_ENTITY = 'rules.Rule'


class RuleAuditType(str, Enum):
    CREATED = 'rules.RULE_CREATED'
    UPDATED = 'rules.RULE_UPDATED'
    DELETED = 'rules.RULE_DELETED'
    ACTIVATED = 'rules.RULE_ACTIVATED'
    DEACTIVATED = 'rules.RULE_DEACTIVATED'
    EVALUATED = 'rules.RULE_EVALUATED'


def rule_created(user_id: Any, rule: Rule) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.user(user_id),
        entity=_rule_entity(rule.pk),
        event_type=RuleAuditType.CREATED.value,
        severity=AuditSeverity.INFO,
        details={'after': _rule_snapshot(rule)},
    )


def rule_updated(user_id: Any, rule_old: Rule, rule_new: Rule) -> AuditRecord:
    old = _rule_snapshot(rule_old)
    new = _rule_snapshot(rule_new)

    changed_fields, before, after = diff_dicts(old, new)

    if not changed_fields:
        return AuditRecord(
            actor=AuditActor.user(user_id),
            entity=_rule_entity(rule_new.pk),
            event_type=RuleAuditType.UPDATED.value,
            severity=AuditSeverity.WARNING,
            details={'reason': 'No changes'},
        )

    return AuditRecord(
        actor=AuditActor.user(user_id),
        entity=_rule_entity(rule_new.pk),
        event_type=RuleAuditType.UPDATED.value,
        severity=AuditSeverity.INFO,
        details={
            'changed_fields': changed_fields,
            'before': before,
            'after': after,
        },
    )


def rule_deleted(user_id: Any, rule: Rule) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.user(user_id),
        entity=_rule_entity(rule.pk),
        event_type=RuleAuditType.DELETED.value,
        severity=AuditSeverity.INFO,
        details={'before': _rule_snapshot(rule)},
    )


def rule_activated(user_id: Any, rule: Rule) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.user(user_id),
        entity=_rule_entity(rule.pk),
        event_type=RuleAuditType.ACTIVATED.value,
        severity=AuditSeverity.INFO,
        details={
            'before': {'is_active': False},
            'after': {'is_active': True},
        },
    )


def rule_deactivated(user_id: Any, rule: Rule) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.user(user_id),
        entity=_rule_entity(rule.pk),
        event_type=RuleAuditType.DEACTIVATED.value,
        severity=AuditSeverity.INFO,
        details={
            'before': {'is_active': True},
            'after': {'is_active': False},
        },
    )


def rule_evaluated(rule_id: Any, details: dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        actor=AuditActor.system(),
        entity=_rule_entity(rule_id),
        event_type=RuleAuditType.EVALUATED.value,
        severity=AuditSeverity.INFO,
        details={**details},
    )


def _rule_entity(rule_id: Any) -> AuditEntity:
    return AuditEntity(type=RULE_AUDIT_ENTITY, id=str(rule_id))


def _rule_snapshot(rule: Rule) -> dict[str, Any]:
    return {
        'name': rule.name,
        'description': rule.description,
        'is_active': rule.is_active,
        'device_metric_id': str(rule.device_metric_id),
        'condition': rule.condition,
        'action': rule.action,
    }
