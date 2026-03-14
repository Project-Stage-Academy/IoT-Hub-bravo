from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    class Actor(models.TextChoices):
        USER = 'user', 'User'
        SYSTEM = 'system', 'System'
        EXTERNAL = 'external', 'External'

    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

    id = models.BigAutoField(primary_key=True, editable=False)
    audit_event_id = models.UUIDField(
        unique=True,
        help_text='Idempotency key (provided by producer)',
    )

    actor_type = models.CharField(
        max_length=20,
        choices=Actor,
        default=Actor.SYSTEM,
    )
    actor_id = models.CharField(max_length=100, null=True, blank=True)

    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)

    event_type = models.CharField(max_length=100)
    severity = models.CharField(
        max_length=20,
        choices=Severity,
        default=Severity.INFO,
    )

    occurred_at = models.DateTimeField(default=timezone.now)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured metadata / payload',
    )

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(
                fields=['entity_type', 'entity_id', 'occurred_at'],
                name='idx_audit_entity_time',
            ),
            models.Index(
                fields=['event_type', 'occurred_at'],
                name='idx_audit_event_time',
            ),
        ]
