from django.db import models
from django.db.models import Case, When, Value
from django.db.models.functions import Cast, KeyTextTransform

class Telemetry(models.Model):
    id = models.BigAutoField(primary_key=True)  
    device_metric = models.ForeignKey('devices.DeviceMetric', on_delete=models.CASCADE, null=False, db_index=True)
    value_jsonb = models.JSONField(null=False)  

    value_numeric = models.GeneratedField(
        expression=Case(
            When(
                KeyTextTransform('t', 'value_jsonb') == Value('numeric'),
                then=Cast(KeyTextTransform('v', 'value_jsonb'), output_field=models.DecimalField())
            ),
            default=None
        ),
        output_field=models.DecimalField(max_digits=20, decimal_places=10, null=True),
        db_persist=True,
    )

    value_bool = models.GeneratedField(
        expression=Case(
            When(
                KeyTextTransform('t', 'value_jsonb') == Value('bool'),
                then=Cast(KeyTextTransform('v', 'value_jsonb'), output_field=models.BooleanField())
            ),
            default=None
        ),
        output_field=models.BooleanField(null=True),
        db_persist=True,
    )

    value_str = models.GeneratedField(
        expression=Case(
            When(
                KeyTextTransform('t', 'value_jsonb') == Value('str'),
                then=KeyTextTransform('v', 'value_jsonb')
            ),
            default=None
        ),
        output_field=models.TextField(null=True),
        db_persist=True,
    )

    ts = models.DateTimeField(default=models.functions.Now(), null=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'telemetries'
        indexes = [
            models.Index(fields=['device_metric', 'ts'], name='idx_telemetries_metric_time'),
            models.Index(fields=['ts'], name='idx_telemetries_timestamp'),
            models.UniqueConstraint(fields=['device_metric', 'ts'], name='unique_telemetry_per_metric_time')
        ]
