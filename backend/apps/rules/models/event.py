from django.db import models
import uuid
from django.utils.timezone import now


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=now)
    rule = models.ForeignKey('rules.Rule', on_delete=models.CASCADE)
    acknowledged = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        db_table = 'events'
        indexes = [
            models.Index(fields=['rule', 'acknowledged'], name='idx_events_rule_ack'),
            models.Index(fields=['timestamp'], name='idx_events_time'),
        ]

    def __str__(self):
        return f"Event {self.id} (rule_id={self.rule_id})"

