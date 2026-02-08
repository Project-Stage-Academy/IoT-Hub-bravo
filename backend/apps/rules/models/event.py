from django.db import models


class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=models.functions.Now(), null=False, db_index=True)
    rule = models.ForeignKey('rules.Rule', on_delete=models.CASCADE, null=False, db_index=True)
    acknowledged = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    trigger_telemetry = models.ForeignKey('devices.Telemetry', 
                                        on_delete=models.SET_NULL, # if telemetry was deleted
                                        null=True,  # backwards compatibility
                                        blank=True,
                                        related_name='triggered_events'
                                        )

    class Meta:
        db_table = 'events'
        indexes = [
            models.Index(fields=['timestamp'], name='idx_events_timestamp'),
            models.Index(fields=['rule'], name='idx_events_rule'),
        ]

    def __str__(self):
        return f"Event {self.id} - {self.rule.name}"
