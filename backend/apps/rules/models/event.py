from django.db import models

from apps.devices.models.telemetry import Telemetry


class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=models.functions.Now(), null=False, db_index=True)
    rule = models.ForeignKey('rules.Rule', on_delete=models.CASCADE, null=False, db_index=True)
    acknowledged = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    trigger_telemetry_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the telemetry that triggered this event",
    )

    def get_trigger_telemetry(self):
        """Safely retrieve trigger telemetry if it still exists"""
        if self.trigger_telemetry_id:
            try:
                return Telemetry.objects.get(id=self.trigger_telemetry_id)
            except Telemetry.DoesNotExist:
                return None

    class Meta:
        db_table = 'events'
        indexes = [
            models.Index(fields=['timestamp'], name='idx_events_timestamp'),
            models.Index(fields=['rule'], name='idx_events_rule'),
            models.Index(fields=['trigger_telemetry_id'], name='idx_events_telemetry_id'),
        ]

    def __str__(self):
        return f"Event {self.id} - {self.rule.name}"
