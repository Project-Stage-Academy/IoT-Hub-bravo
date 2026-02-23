import pytest
from django.utils import timezone
from django.db import IntegrityError, connection, transaction

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event

pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="pass123"
    )


@pytest.fixture
def device(user):
    return Device.objects.create(user=user, serial_id="DEV-001", name="Test Device")


@pytest.fixture
def metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric(device, metric):
    return DeviceMetric.objects.create(device=device, metric=metric)


@pytest.fixture
def rule(device_metric):
    return Rule.objects.create(
        name="High Temp Rule",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action="notify",
        is_active=True,
    )


@pytest.fixture
def event(rule):
    return Event.objects.create(rule=rule)


# ============================================================================
# Field defaults
# ============================================================================


def test_event_default_acknowledged_is_false(rule):
    event = Event.objects.create(rule=rule)
    assert event.acknowledged is False


def test_event_timestamp_is_auto_set(rule):
    before = timezone.now()
    event = Event.objects.create(rule=rule)
    after = timezone.now()
    assert before <= event.timestamp <= after


def test_event_created_at_is_auto_set(rule):
    before = timezone.now()
    event = Event.objects.create(rule=rule)
    after = timezone.now()
    assert before <= event.created_at <= after


def test_event_trigger_fields_default_to_null(rule):
    event = Event.objects.create(rule=rule)
    assert event.trigger_telemetry_id is None
    assert event.trigger_device_id is None


# ============================================================================
# Field assignment
# ============================================================================


def test_event_can_store_trigger_telemetry_id(rule):
    event = Event.objects.create(rule=rule, trigger_telemetry_id=42)
    assert event.trigger_telemetry_id == 42


def test_event_can_store_trigger_device_id(rule):
    event = Event.objects.create(rule=rule, trigger_device_id=99)
    assert event.trigger_device_id == 99


def test_event_can_be_created_with_explicit_acknowledged_true(rule):
    event = Event.objects.create(rule=rule, acknowledged=True)
    assert event.acknowledged is True


def test_event_can_be_created_with_explicit_timestamp(rule):
    ts = timezone.now()
    event = Event.objects.create(rule=rule, timestamp=ts)
    # Stored and retrieved timestamp should be equal within microsecond precision
    assert abs((event.timestamp - ts).total_seconds()) < 1


# ============================================================================
# Constraints
# ============================================================================


def test_event_rule_is_required():
    # PostgreSQL defers FK checks within the test transaction.
    # Wrap in a savepoint and call check_constraints() to force immediate evaluation.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Event.objects.create(rule_id=99999)
            connection.check_constraints()


def test_event_cascade_delete_when_rule_deleted(rule):
    event = Event.objects.create(rule=rule)
    event_id = event.id
    rule.delete()
    assert not Event.objects.filter(id=event_id).exists()


# ============================================================================
# get_trigger_telemetry helper
# ============================================================================


def test_get_trigger_telemetry_returns_none_when_id_is_null(rule):
    event = Event.objects.create(rule=rule)
    assert event.get_trigger_telemetry() is None


def test_get_trigger_telemetry_returns_none_for_nonexistent_id(rule):
    event = Event.objects.create(rule=rule, trigger_telemetry_id=999999)
    assert event.get_trigger_telemetry() is None


def test_get_trigger_telemetry_returns_object_when_telemetry_exists(rule, device_metric):
    telemetry = Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": 75},
    )
    event = Event.objects.create(rule=rule, trigger_telemetry_id=telemetry.id)
    retrieved = event.get_trigger_telemetry()
    assert retrieved is not None
    assert retrieved.id == telemetry.id


# ============================================================================
# __str__
# ============================================================================


def test_event_str_representation(rule):
    event = Event.objects.create(rule=rule)
    assert str(event) == f"Event {event.id} - {rule.name}"


# ============================================================================
# Acknowledgement update
# ============================================================================


def test_event_can_be_acknowledged_via_save(rule):
    event = Event.objects.create(rule=rule)
    assert event.acknowledged is False

    event.acknowledged = True
    event.save(update_fields=["acknowledged"])
    event.refresh_from_db()

    assert event.acknowledged is True


def test_event_acknowledged_is_idempotent(rule):
    event = Event.objects.create(rule=rule, acknowledged=True)
    event.acknowledged = True
    event.save(update_fields=["acknowledged"])
    event.refresh_from_db()
    assert event.acknowledged is True


# ============================================================================
# Meta / DB table
# ============================================================================


def test_event_db_table_name():
    assert Event._meta.db_table == "events"


def test_event_verbose_name():
    assert Event._meta.verbose_name == "Event"
    assert Event._meta.verbose_name_plural == "Events"


def test_event_has_expected_indexes():
    index_field_sets = [set(idx.fields) for idx in Event._meta.indexes]
    assert {"timestamp"} in index_field_sets
    assert {"rule"} in index_field_sets
    assert {"acknowledged"} in index_field_sets
