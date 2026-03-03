from django.db import models
from django.utils import timezone


class DeliveryType(models.TextChoices):
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"


class Status(models.TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY = "retry"
    SUCCESS = "success"
    REJECTED = "rejected"


class EventDelivery(models.Model):
    rule_id = models.IntegerField()

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
    )

    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)

    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    response_status = models.IntegerField(null=True, blank=True)

    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "event_deliveries"
        verbose_name = "Event Delivery"
        verbose_name_plural = "Event Deliveries"
        indexes = [
            models.Index(fields=["status"], name="idx_event_deliveries_status"),
            models.Index(
                fields=["status", "next_retry_at"], name="idx_event_deliveries_status_retry"
            ),
            models.Index(
                fields=["status", "updated_at"], name="idx_event_deliveries_status_updated"
            ),
        ]
