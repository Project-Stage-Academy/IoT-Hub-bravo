# import pytest
# from django.utils import timezone
# from datetime import timedelta

# from apps.rules.models.event_delivery import EventDelivery, DeliveryType, Status

# pytestmark = pytest.mark.django_db


# # ============================================================================
# # Helpers
# # ============================================================================


# def make_delivery(**kwargs):
#     defaults = dict(
#         rule_id=1,
#         delivery_type=DeliveryType.WEBHOOK,
#         payload={"url": "https://example.com/hook", "body": {"alert": "test"}},
#     )
#     defaults.update(kwargs)
#     return EventDelivery.objects.create(**defaults)


# # ============================================================================
# # Default field values
# # ============================================================================


# def test_event_delivery_default_status_is_pending():
#     delivery = make_delivery()
#     assert delivery.status == Status.PENDING


# def test_event_delivery_default_attempts_is_zero():
#     delivery = make_delivery()
#     assert delivery.attempts == 0


# def test_event_delivery_default_max_attempts_is_five():
#     delivery = make_delivery()
#     assert delivery.max_attempts == 5


# def test_event_delivery_last_attempt_at_defaults_to_null():
#     delivery = make_delivery()
#     assert delivery.last_attempt_at is None


# def test_event_delivery_next_retry_at_defaults_to_null():
#     delivery = make_delivery()
#     assert delivery.next_retry_at is None


# def test_event_delivery_response_status_defaults_to_null():
#     delivery = make_delivery()
#     assert delivery.response_status is None


# def test_event_delivery_error_message_defaults_to_null():
#     delivery = make_delivery()
#     assert delivery.error_message is None


# def test_event_delivery_created_at_is_set_on_create():
#     before = timezone.now()
#     delivery = make_delivery()
#     after = timezone.now()
#     assert before <= delivery.created_at <= after


# def test_event_delivery_updated_at_is_set_on_create():
#     before = timezone.now()
#     delivery = make_delivery()
#     after = timezone.now()
#     assert before <= delivery.updated_at <= after


# # ============================================================================
# # DeliveryType choices
# # ============================================================================


# def test_event_delivery_webhook_type():
#     delivery = make_delivery(delivery_type=DeliveryType.WEBHOOK)
#     assert delivery.delivery_type == "webhook"


# def test_event_delivery_notification_type():
#     delivery = make_delivery(delivery_type=DeliveryType.NOTIFICATION)
#     assert delivery.delivery_type == "notification"


# # ============================================================================
# # Status choices
# # ============================================================================


# @pytest.mark.parametrize(
#     "status",
#     [
#         Status.PENDING,
#         Status.PROCESSING,
#         Status.RETRY,
#         Status.SUCCESS,
#         Status.REJECTED,
#     ],
# )
# def test_event_delivery_all_statuses_are_storable(status):
#     delivery = make_delivery(status=status)
#     delivery.refresh_from_db()
#     assert delivery.status == status


# # ============================================================================
# # Field assignment and updates
# # ============================================================================


# def test_event_delivery_can_store_json_payload():
#     payload = {"key": "value", "nested": {"a": 1}}
#     delivery = make_delivery(payload=payload)
#     delivery.refresh_from_db()
#     assert delivery.payload == payload


# def test_event_delivery_can_update_status_to_success():
#     delivery = make_delivery()
#     delivery.status = Status.SUCCESS
#     delivery.save(update_fields=["status"])
#     delivery.refresh_from_db()
#     assert delivery.status == Status.SUCCESS


# def test_event_delivery_can_update_status_to_rejected():
#     delivery = make_delivery()
#     delivery.status = Status.REJECTED
#     delivery.save(update_fields=["status"])
#     delivery.refresh_from_db()
#     assert delivery.status == Status.REJECTED


# def test_event_delivery_attempts_can_be_incremented():
#     delivery = make_delivery()
#     delivery.attempts = 3
#     delivery.save(update_fields=["attempts"])
#     delivery.refresh_from_db()
#     assert delivery.attempts == 3


# def test_event_delivery_max_attempts_can_be_customized():
#     delivery = make_delivery(max_attempts=10)
#     assert delivery.max_attempts == 10


# def test_event_delivery_last_attempt_at_can_be_set():
#     now = timezone.now()
#     delivery = make_delivery(last_attempt_at=now)
#     delivery.refresh_from_db()
#     assert abs((delivery.last_attempt_at - now).total_seconds()) < 1


# def test_event_delivery_next_retry_at_can_be_set():
#     future = timezone.now() + timedelta(minutes=5)
#     delivery = make_delivery(next_retry_at=future)
#     delivery.refresh_from_db()
#     assert abs((delivery.next_retry_at - future).total_seconds()) < 1


# def test_event_delivery_response_status_can_be_set():
#     delivery = make_delivery(response_status=200)
#     delivery.refresh_from_db()
#     assert delivery.response_status == 200


# def test_event_delivery_error_message_can_be_set():
#     delivery = make_delivery(error_message="Connection refused")
#     delivery.refresh_from_db()
#     assert delivery.error_message == "Connection refused"


# def test_event_delivery_rule_id_is_stored():
#     delivery = make_delivery(rule_id=42)
#     assert delivery.rule_id == 42


# # ============================================================================
# # Retry / attempt scenario
# # ============================================================================


# def test_event_delivery_retry_flow():
#     """Simulate a typical retry cycle: pending → processing → retry → success"""
#     delivery = make_delivery()
#     assert delivery.status == Status.PENDING

#     delivery.status = Status.PROCESSING
#     delivery.attempts = 1
#     delivery.last_attempt_at = timezone.now()
#     delivery.save(update_fields=["status", "attempts", "last_attempt_at"])
#     delivery.refresh_from_db()
#     assert delivery.status == Status.PROCESSING
#     assert delivery.attempts == 1

#     delivery.status = Status.RETRY
#     delivery.error_message = "Timeout"
#     delivery.next_retry_at = timezone.now() + timedelta(minutes=2)
#     delivery.save(update_fields=["status", "error_message", "next_retry_at"])
#     delivery.refresh_from_db()
#     assert delivery.status == Status.RETRY
#     assert delivery.error_message == "Timeout"

#     delivery.status = Status.SUCCESS
#     delivery.response_status = 200
#     delivery.attempts = 2
#     delivery.save(update_fields=["status", "response_status", "attempts"])
#     delivery.refresh_from_db()
#     assert delivery.status == Status.SUCCESS
#     assert delivery.response_status == 200
#     assert delivery.attempts == 2


# def test_event_delivery_rejected_after_max_attempts():
#     delivery = make_delivery(max_attempts=3)

#     delivery.attempts = 3
#     delivery.status = Status.REJECTED
#     delivery.error_message = "Max attempts reached"
#     delivery.save(update_fields=["attempts", "status", "error_message"])
#     delivery.refresh_from_db()

#     assert delivery.status == Status.REJECTED
#     assert delivery.attempts == delivery.max_attempts
#     assert "Max attempts" in delivery.error_message


# # ============================================================================
# # Meta / DB table
# # ============================================================================


# def test_event_delivery_db_table_name():
#     assert EventDelivery._meta.db_table == "event_deliveries"


# def test_event_delivery_verbose_name():
#     assert EventDelivery._meta.verbose_name == "Event Delivery"
#     assert EventDelivery._meta.verbose_name_plural == "Event Deliveries"


# def test_event_delivery_has_status_index():
#     index_field_sets = [set(idx.fields) for idx in EventDelivery._meta.indexes]
#     assert {"status"} in index_field_sets


# def test_event_delivery_has_status_next_retry_at_index():
#     index_field_sets = [set(idx.fields) for idx in EventDelivery._meta.indexes]
#     assert {"status", "next_retry_at"} in index_field_sets
