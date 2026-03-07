import uuid

import pytest

from apps.audit.models import AuditLog
from apps.audit.types import AuditLogCreateData
from apps.audit.services.audit_log_services import (
    audit_log_create_batch,
    REQUIRED_FIELDS,
)


@pytest.fixture
def audit_create_entry() -> AuditLogCreateData:
    """Base valid AuditLogCreateData payload."""
    return {
        "audit_event_id": uuid.uuid4(),
        "entity_type": "rules.Rule",
        "entity_id": "42",
        "event_type": "rules.RULE_UPDATED",
        "details": {"changed_fields": ["name"]},
    }


@pytest.fixture
def make_entry(audit_create_entry):
    """Factory to create AuditLogCreateData with overrides."""

    def _make(**overrides) -> AuditLogCreateData:
        entry = dict(audit_create_entry)
        entry["audit_event_id"] = uuid.uuid4()
        entry.update(overrides)
        return entry

    return _make


@pytest.mark.django_db
def test_empty_batch_returns_zero_counts():
    """Test empty batch returns attempted=0 and created=0."""
    result = audit_log_create_batch([])
    assert result.attempted == 0
    assert result.created == 0
    assert result.errors == {}


@pytest.mark.django_db
def test_creates_single_audit_log(make_entry):
    """Test a valid single entry is inserted."""
    entry = make_entry()
    result = audit_log_create_batch([entry])

    assert result.attempted == 1
    assert result.created == 1
    assert result.errors == {}
    assert AuditLog.objects.count() == 1

    obj = AuditLog.objects.get()
    assert obj.audit_event_id == entry["audit_event_id"]
    assert obj.entity_type == entry["entity_type"]
    assert obj.entity_id == entry["entity_id"]
    assert obj.event_type == entry["event_type"]


@pytest.mark.django_db
def test_duplicate_audit_event_id_in_batch_is_reported(make_entry):
    """Test duplicated audit_event_id are reported in result."""
    audit_event_id = uuid.uuid4()
    entry1 = make_entry(audit_event_id=audit_event_id)
    entry2 = make_entry(audit_event_id=audit_event_id)

    result = audit_log_create_batch([entry1, entry2])

    assert result.attempted == 2
    assert result.created == 1
    assert 1 in result.errors
    assert "audit_event_id" in result.errors[1]
    assert AuditLog.objects.count() == 1


@pytest.mark.django_db
def test_invalid_actor_type_is_reported(make_entry):
    """Test invalid actor_type is rejected with field error."""
    entry = make_entry(actor_type="invalid-actor")

    result = audit_log_create_batch([entry])

    assert result.attempted == 1
    assert result.created == 0
    assert 0 in result.errors
    assert "actor_type" in result.errors[0]
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_invalid_severity_is_reported(make_entry):
    """Test invalid severity is rejected with field error."""
    entry = make_entry(severity="invalid-severity")

    result = audit_log_create_batch([entry])

    assert result.attempted == 1
    assert result.created == 0
    assert 0 in result.errors
    assert "severity" in result.errors[0]
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_actor_type_and_severity_are_normalized_to_lowercase(make_entry):
    """Test actor_type/severity are normalized to lowercase before insert."""
    entry = make_entry(actor_type="SyStEm", severity="InFo")

    result = audit_log_create_batch([entry])

    assert result.created == 1
    assert result.errors == {}

    obj = AuditLog.objects.get(audit_event_id=entry["audit_event_id"])
    assert obj.actor_type == "system"
    assert obj.severity == "info"


@pytest.mark.django_db
@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_missing_required_fields_are_reported(make_entry, field):
    """Test missing required fields are reported."""
    entry = make_entry()
    entry.pop(field)

    result = audit_log_create_batch([entry])

    assert result.attempted == 1
    assert result.created == 0
    assert 0 in result.errors
    assert field in result.errors[0]
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_ignore_conflicts_skips_existing_audit_event_id(make_entry):
    """Test existing audit_event_id does not create duplicates."""
    audit_event_id = uuid.uuid4()

    AuditLog.objects.create(
        audit_event_id=audit_event_id,
        entity_type="rules.Rule",
        entity_id="1",
        event_type="rules.RULE_CREATED",
    )

    entry = make_entry(audit_event_id=audit_event_id, entity_id="2")

    result = audit_log_create_batch([entry])

    assert result.attempted == 1
    assert AuditLog.objects.filter(audit_event_id=audit_event_id).count() == 1
