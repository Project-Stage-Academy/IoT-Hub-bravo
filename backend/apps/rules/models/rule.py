from django.db import models


class Rule(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(blank=True, null=True)
    condition = models.JSONField(null=False)
    action = models.JSONField(null=False)
    is_active = models.BooleanField(default=True, db_index=True)
    device_metric = models.ForeignKey(
        'devices.DeviceMetric', on_delete=models.CASCADE, null=False, db_index=True
    )

    class Meta:
        db_table = 'rules'
        indexes = [
            models.Index(fields=['device_metric'], name='idx_rules_device_metric'),
            models.Index(fields=['is_active'], name='idx_rules_is_active'),
        ]
