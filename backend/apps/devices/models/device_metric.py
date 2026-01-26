from django.db import models


class DeviceMetric(models.Model):
    id = models.AutoField(primary_key=True)
    device = models.ForeignKey(
        'devices.Device', on_delete=models.CASCADE, null=False, db_index=True
    )
    metric = models.ForeignKey(
        'devices.Metric', on_delete=models.RESTRICT, null=False, db_index=True
    )

    class Meta:
        db_table = 'device_metrics'
        unique_together = ('device', 'metric')
        indexes = [
            models.Index(fields=['device'], name='idx_device_metrics_device'),
            models.Index(fields=['metric'], name='idx_device_metrics_metric'),
        ]
