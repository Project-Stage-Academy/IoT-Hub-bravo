import datetime
import uuid

import pytest

from apps.audit.serializers.audit_log_serializers import (
    AuditLogSerializer,
    AuditLogBatchSerializer,
)


@pytest.fixture
def valid_audit_log_payload():
    """Valid audit log JSON payload."""
    return {
        'audit_event_id': str(uuid.uuid4()),
        'entity_type': 'rules.Rule',
        'entity_id': 123,
        'event_type': 'rules.RULE_UPDATED',
        'actor_type': 'user',
        'actor_id': 123,
        'severity': 'info',
        'occurred_at': '2026-02-04T12:00:00Z',
        'details': {'changed_fields': ['name'], 'before': {'name': 'A'}, 'after': {'name': 'B'}},
    }


def test_audit_serializer_valid_payload(valid_audit_log_payload):
    """Test valid payload is accepted and normalized."""
    s = AuditLogSerializer(valid_audit_log_payload)
    assert s.is_valid() is True, s.errors

    data = s.validated_data

    assert isinstance(data['audit_event_id'], uuid.UUID)
    assert isinstance(data['occurred_at'], datetime.datetime)
    assert isinstance(data['details'], dict)

    assert data['entity_type'] == valid_audit_log_payload['entity_type']
    assert data['entity_id'] == str(valid_audit_log_payload['entity_id'])
    assert data['event_type'] == valid_audit_log_payload['event_type']
    assert data['actor_type'] == valid_audit_log_payload['actor_type']
    assert data['actor_id'] == str(valid_audit_log_payload['actor_id'])
    assert data['severity'] == valid_audit_log_payload['severity']


def test_audit_serializer_rejects_non_dict_payload():
    """Test non-dict payload is rejected."""
    s = AuditLogSerializer(['not-a-dict'])
    assert s.is_valid() is False
    assert 'non_field_errors' in s.errors


@pytest.mark.parametrize(
    'missing_field',
    ['audit_event_id', 'entity_type', 'entity_id', 'event_type'],
)
def test_audit_serializer_missing_required_field(valid_audit_log_payload, missing_field):
    """Test missing required field returns an error."""
    payload = dict(valid_audit_log_payload)
    payload.pop(missing_field)

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert missing_field in s.errors


@pytest.mark.parametrize(
    'missing_field',
    ['actor_type', 'actor_id', 'severity', 'occurred_at', 'details'],
)
def test_audit_serializer_optional_none_is_omitted(valid_audit_log_payload, missing_field):
    """Test optional field set to None is omitted from validated_data."""
    payload = dict(valid_audit_log_payload)
    payload.pop(missing_field)

    s = AuditLogSerializer(payload)
    assert s.is_valid() is True, s.errors

    data = s.validated_data
    assert missing_field not in data


@pytest.mark.parametrize(
    'field, invalid_value',
    [
        ('audit_event_id', 123),
        ('entity_type', 123),
        ('entity_id', {'invalid': 'id'}),
        ('event_type', 123),
        ('details', 'not-a-dict'),
        ('occurred_at', 123),
    ],
)
def test_audit_serializer_wrong_field_types(valid_audit_log_payload, field, invalid_value):
    """Test wrong field types are rejected with error messages."""
    payload = dict(valid_audit_log_payload)
    payload[field] = invalid_value

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert field in s.errors


def test_audit_serializer_invalid_uuid_is_rejected(valid_audit_log_payload):
    """Test invalid audit_event_id is rejected."""
    payload = dict(valid_audit_log_payload)
    payload['audit_event_id'] = 'invalid-uuid'

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert 'audit_event_id' in s.errors


@pytest.mark.parametrize('value', ['', '   ', '\n\t'])
def test_audit_serializer_required_strings_must_be_non_empty(valid_audit_log_payload, value):
    """Test required string fields must be non-empty after trimming."""
    payload = dict(valid_audit_log_payload)
    payload['entity_type'] = value

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert 'entity_type' in s.errors


def test_audit_serializer_entity_id_int_is_normalized_to_str(valid_audit_log_payload):
    """Test entity_id int is normalized to string."""
    payload = dict(valid_audit_log_payload)
    payload['entity_id'] = 123

    s = AuditLogSerializer(payload)
    assert s.is_valid() is True, s.errors
    assert s.validated_data['entity_id'] == '123'


def test_audit_serializer_invalid_occurred_at_is_rejected(valid_audit_log_payload):
    """Test invalid ISO-8601 occurred_at is rejected."""
    payload = dict(valid_audit_log_payload)
    payload['occurred_at'] = 'not-a-datetime'

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert 'occurred_at' in s.errors
    assert s.errors['occurred_at'] == 'occurred_at must be a valid ISO-8601 datetime.'


def test_audit_serializer_details_invalid_key_is_rejected(valid_audit_log_payload):
    """Test details keys must be non-empty strings."""
    payload = dict(valid_audit_log_payload)
    payload['details'] = {'\n  \t': 1, 'ok': 2}

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert 'details' in s.errors


def test_audit_serializer_details_non_serializable_value_is_rejected(valid_audit_log_payload):
    """Test details values must be JSON-serializable."""
    payload = dict(valid_audit_log_payload)
    payload['details'] = {'invalid': set([1, 2, 3])}

    s = AuditLogSerializer(payload)
    assert s.is_valid() is False
    assert 'details' in s.errors
    assert 'invalid' in s.errors['details']


def test_audit_serializer_omits_optional_nones(valid_audit_log_payload):
    """Test optional fields are omitted when not provided."""
    payload = dict(valid_audit_log_payload)
    payload.pop('actor_id')
    payload.pop('details')

    s = AuditLogSerializer(payload)
    assert s.is_valid() is True, s.errors
    data = s.validated_data
    assert 'actor_id' not in data
    assert 'details' not in data


def test_audit_batch_serializer_rejects_non_list_payload():
    """Test batch serializer rejects non-list payload."""
    s = AuditLogBatchSerializer({'not': 'a list'})
    assert s.is_valid() is False
    assert 'non_field_errors' in s.errors


def test_audit_batch_serializer_empty_list_returns_error():
    """Test empty batch returns errors."""
    s = AuditLogBatchSerializer([])
    assert s.is_valid() is False
    assert 'items' in s.errors
    assert 'non_field_errors' in s.errors['items']


def test_audit_batch_serializer_mixed_valid_and_invalid_items(valid_audit_log_payload):
    """Test batch serializer collects item_errors for invalid items."""
    valid_item = dict(valid_audit_log_payload)

    invalid_item = dict(valid_audit_log_payload)
    invalid_item['audit_event_id'] = 'not-a-uuid'

    payload = [valid_item, invalid_item, valid_item]

    s = AuditLogBatchSerializer(payload)
    assert s.is_valid() is False

    assert len(s.valid_items) == 2
    assert 1 in s.item_errors
    assert 'audit_event_id' in s.item_errors[1]


def test_audit_batch_serializer_all_invalid_items_returns_errors(valid_audit_log_payload):
    """Test batch serializer with all invalid items returns errors."""
    invalid1 = dict(valid_audit_log_payload)
    invalid1.pop('entity_type')

    invalid2 = dict(valid_audit_log_payload)
    invalid2['occurred_at'] = 'invalid'

    s = AuditLogBatchSerializer([invalid1, invalid2])
    assert s.is_valid() is False

    assert 'items' in s.errors
    assert 0 in s.errors['items']
    assert 1 in s.errors['items']
    assert 'entity_type' in s.errors['items'][0]
    assert 'occurred_at' in s.errors['items'][1]
