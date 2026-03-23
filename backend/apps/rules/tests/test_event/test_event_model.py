import pytest
from django.utils import timezone

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric
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
    return Event.objects.create(rule=rule.pk)


# ============================================================================
# Field defaults
# ============================================================================


def test_event_default_acknowledged_is_false(rule):
    event = Event.objects.create(rule=rule.pk)
    assert event.acknowledged is False


def test_event_timestamp_is_auto_set(rule):
    before = timezone.now()
    event = Event.objects.create(rule=rule.pk)
    after = timezone.now()
    assert before <= event.rule_triggered_at <= after


def test_event_created_at_is_auto_set(rule):
    before = timezone.now()
    event = Event.objects.create(rule=rule.pk)
    after = timezone.now()
    assert before <= event.created_at <= after


def test_event_trigger_fields_default_to_null(rule):
    event = Event.objects.create(rule=rule.pk, trigger_device_serial_id="DEV-001")
    assert event.trigger_context is None


# ============================================================================
# Field assignment
# ============================================================================


def test_event_can_store_trigger_device_serial_id(rule):
    event = Event.objects.create(rule=rule.pk, trigger_device_serial_id="SN-00042")
    assert event.trigger_device_serial_id == "SN-00042"


def test_event_can_store_trigger_context(rule):
    ctx = {"telemetry_id": 99, "value": {"t": "numeric", "v": "42.0"}}
    event = Event.objects.create(
        rule=rule.pk, trigger_device_serial_id="SN-00042", trigger_context=ctx
    )
    assert event.trigger_context == ctx


def test_event_can_be_created_with_explicit_acknowledged_true(rule):
    event = Event.objects.create(rule=rule.pk, acknowledged=True)
    assert event.acknowledged is True


def test_event_can_be_created_with_explicit_timestamp(rule):
    ts = timezone.now()
    event = Event.objects.create(rule=rule.pk, rule_triggered_at=ts)
    # Stored and retrieved timestamp should be equal within microsecond precision
    assert abs((event.rule_triggered_at - ts).total_seconds()) < 1


# ============================================================================
# __str__
# ============================================================================


def test_event_str_representation(rule):
    event = Event.objects.create(rule=rule.pk)
    assert str(event) == f"Event {event.event_uuid} - Rule {rule.pk}"


# ============================================================================
# Acknowledgement update
# ============================================================================


def test_event_can_be_acknowledged_via_save(rule):
    event = Event.objects.create(rule=rule.pk)
    assert event.acknowledged is False

    event.acknowledged = True
    event.save(update_fields=["acknowledged"])
    event.refresh_from_db()

    assert event.acknowledged is True


def test_event_acknowledged_is_idempotent(rule):
    event = Event.objects.create(rule=rule.pk, acknowledged=True)
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
    assert {"rule_triggered_at"} in index_field_sets
    assert {"rule"} in index_field_sets
    assert {"acknowledged"} in index_field_sets
    assert {"trigger_device_serial_id"} in index_field_sets
