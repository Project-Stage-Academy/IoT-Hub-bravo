from django.db import models

from django.utils import timezone
import uuid


class Event(models.Model):
    event_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    rule_triggered_at = models.DateTimeField(default=timezone.now, null=False)
    rule = models.ForeignKey('rules.Rule', on_delete=models.CASCADE, null=False)
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    trigger_device_serial_id = models.CharField(max_length=255, null=False)

    trigger_context = models.JSONField(
        null=True,
        blank=True,
        help_text="Flexible context about what triggered the event (e.g., telemetry values, thresholds)",
    )

    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"
        db_table = 'events'
        indexes = [
            models.Index(fields=['rule_triggered_at'], name='idx_events_rule_triggered_at'),
            models.Index(fields=['rule'], name='idx_events_rule'),
            models.Index(fields=['acknowledged'], name='idx_events_ack'),
            models.Index(fields=['trigger_device_serial_id'], name='idx_events_device_serial_id'),
        ]

    def __str__(self):
        return f"Event {self.event_uuid} - {self.rule.name}"
