import pytest
import uuid
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError, transaction

from apps.rules.models.event_delivery import EventDelivery, DeliveryType, Status

pytestmark = pytest.mark.django_db


# ============================================================================
# Helpers
# ============================================================================


def make_delivery(**kwargs):
    """Create an EventDelivery with safe defaults for all required fields."""
    defaults = dict(
        event_uuid=uuid.uuid4(),
        rule_id=1,
        trigger_device_serial_id="DEV-001",
        delivery_type=DeliveryType.WEBHOOK,
        payload={"url": "https://example.com/hook", "body": {"alert": "test"}},
    )
    defaults.update(kwargs)
    return EventDelivery.objects.create(**defaults)


# ============================================================================
# Default field values
# ============================================================================


def test_event_delivery_default_status_is_pending():
    delivery = make_delivery()
    assert delivery.status == Status.PENDING


def test_event_delivery_default_attempts_is_zero():
    delivery = make_delivery()
    assert delivery.attempts == 0


def test_event_delivery_default_max_attempts_is_five():
    delivery = make_delivery()
    assert delivery.max_attempts == 5


def test_event_delivery_last_attempt_at_defaults_to_null():
    delivery = make_delivery()
    assert delivery.last_attempt_at is None


def test_event_delivery_next_retry_at_defaults_to_null():
    delivery = make_delivery()
    assert delivery.next_retry_at is None


def test_event_delivery_response_status_defaults_to_null():
    delivery = make_delivery()
    assert delivery.response_status is None


def test_event_delivery_error_message_defaults_to_null():
    delivery = make_delivery()
    assert delivery.error_message is None


def test_event_delivery_created_at_is_set_on_create():
    before = timezone.now()
    delivery = make_delivery()
    after = timezone.now()
    assert before <= delivery.created_at <= after


def test_event_delivery_updated_at_is_set_on_create():
    before = timezone.now()
    delivery = make_delivery()
    after = timezone.now()
    assert before <= delivery.updated_at <= after


# ============================================================================
# DeliveryType choices
# ============================================================================


def test_event_delivery_webhook_type():
    delivery = make_delivery(delivery_type=DeliveryType.WEBHOOK)
    assert delivery.delivery_type == "webhook"


def test_event_delivery_notification_type():
    delivery = make_delivery(delivery_type=DeliveryType.NOTIFICATION)
    assert delivery.delivery_type == "notification"


# ============================================================================
# Status choices
# ============================================================================


@pytest.mark.parametrize(
    "status",
    [
        Status.PENDING,
        Status.PROCESSING,
        Status.RETRY,
        Status.SUCCESS,
        Status.REJECTED,
    ],
)
def test_event_delivery_all_statuses_are_storable(status):
    delivery = make_delivery(status=status)
    delivery.refresh_from_db()
    assert delivery.status == status


# ============================================================================
# UniqueConstraint: event_uuid + delivery_type
# ============================================================================


def test_unique_constraint_raises_on_duplicate_event_uuid_and_delivery_type():
    """
    The DB constraint 'unique_event_delivery_type' prevents two records with
    the same (event_uuid, delivery_type) pair — i.e. the same event cannot
    have two WEBHOOK deliveries.
    """
    shared_uuid = uuid.uuid4()
    make_delivery(event_uuid=shared_uuid, delivery_type=DeliveryType.WEBHOOK)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_delivery(event_uuid=shared_uuid, delivery_type=DeliveryType.WEBHOOK)


def test_unique_constraint_allows_different_delivery_types_for_same_event():
    """
    Same event_uuid CAN have both WEBHOOK and NOTIFICATION deliveries.
    Only the (event_uuid, delivery_type) pair must be unique.
    """
    shared_uuid = uuid.uuid4()
    webhook = make_delivery(event_uuid=shared_uuid, delivery_type=DeliveryType.WEBHOOK)
    notification = make_delivery(event_uuid=shared_uuid, delivery_type=DeliveryType.NOTIFICATION)

    assert webhook.pk != notification.pk
    assert EventDelivery.objects.filter(event_uuid=shared_uuid).count() == 2


def test_unique_constraint_allows_same_delivery_type_for_different_events():
    """Different event UUIDs can both have a WEBHOOK delivery — no collision."""
    make_delivery(event_uuid=uuid.uuid4(), delivery_type=DeliveryType.WEBHOOK)
    make_delivery(event_uuid=uuid.uuid4(), delivery_type=DeliveryType.WEBHOOK)
    assert EventDelivery.objects.count() == 2


# ============================================================================
# Field assignment and updates
# ============================================================================


def test_event_delivery_can_store_json_payload():
    payload = {"key": "value", "nested": {"a": 1}}
    delivery = make_delivery(payload=payload)
    delivery.refresh_from_db()
    assert delivery.payload == payload


def test_event_delivery_can_update_status_to_success():
    delivery = make_delivery()
    delivery.status = Status.SUCCESS
    delivery.save(update_fields=["status"])
    delivery.refresh_from_db()
    assert delivery.status == Status.SUCCESS


def test_event_delivery_can_update_status_to_rejected():
    delivery = make_delivery()
    delivery.status = Status.REJECTED
    delivery.save(update_fields=["status"])
    delivery.refresh_from_db()
    assert delivery.status == Status.REJECTED


def test_event_delivery_attempts_can_be_incremented():
    delivery = make_delivery()
    delivery.attempts = 3
    delivery.save(update_fields=["attempts"])
    delivery.refresh_from_db()
    assert delivery.attempts == 3


def test_event_delivery_max_attempts_can_be_customized():
    delivery = make_delivery(max_attempts=10)
    assert delivery.max_attempts == 10


def test_event_delivery_last_attempt_at_can_be_set():
    now = timezone.now()
    delivery = make_delivery(last_attempt_at=now)
    delivery.refresh_from_db()
    assert abs((delivery.last_attempt_at - now).total_seconds()) < 1


def test_event_delivery_next_retry_at_can_be_set():
    future = timezone.now() + timedelta(minutes=5)
    delivery = make_delivery(next_retry_at=future)
    delivery.refresh_from_db()
    assert abs((delivery.next_retry_at - future).total_seconds()) < 1


def test_event_delivery_response_status_can_be_set():
    delivery = make_delivery(response_status=200)
    delivery.refresh_from_db()
    assert delivery.response_status == 200


def test_event_delivery_error_message_can_be_set():
    delivery = make_delivery(error_message="Connection refused")
    delivery.refresh_from_db()
    assert delivery.error_message == "Connection refused"


def test_event_delivery_rule_id_is_stored():
    delivery = make_delivery(rule_id=42)
    assert delivery.rule_id == 42

# ============================================================================
# Meta / DB table
# ============================================================================


def test_event_delivery_db_table_name():
    assert EventDelivery._meta.db_table == "event_deliveries"


def test_event_delivery_verbose_name():
    assert EventDelivery._meta.verbose_name == "Event Delivery"
    assert EventDelivery._meta.verbose_name_plural == "Event Deliveries"


def test_event_delivery_has_status_index():
    index_field_sets = [set(idx.fields) for idx in EventDelivery._meta.indexes]
    assert {"status"} in index_field_sets


def test_event_delivery_has_status_next_retry_at_index():
    index_field_sets = [set(idx.fields) for idx in EventDelivery._meta.indexes]
    assert {"status", "next_retry_at"} in index_field_sets


def test_event_delivery_has_unique_constraint():
    constraint_names = [c.name for c in EventDelivery._meta.constraints]
    assert "unique_event_delivery_type" in constraint_names
