from django.db import models
from django.db.models import Case, When, Value, DecimalField
from django.db.models.functions import Cast
from django.db.models.fields.json import KeyTextTransform
from django.utils import timezone


class Telemetry(models.Model):
    id = models.BigAutoField(primary_key=True)
    device_metric = models.ForeignKey(
        "devices.DeviceMetric", on_delete=models.CASCADE, null=False, db_index=True
    )
    value_jsonb = models.JSONField(null=False)

    value_numeric = models.GeneratedField(
        expression=Case(
            When(
                value_jsonb__t="numeric",
                then=Cast(
                    KeyTextTransform("v", "value_jsonb"),
                    output_field=DecimalField(max_digits=20, decimal_places=10),
                ),
            ),
            default=Value(
                None, output_field=DecimalField(max_digits=20, decimal_places=10)
            ),
        ),
        output_field=DecimalField(max_digits=20, decimal_places=10),
        db_persist=True,
    )

    value_bool = models.GeneratedField(
        expression=Case(
            When(
                value_jsonb__t="bool",
                then=Cast(
                    KeyTextTransform("v", "value_jsonb"),
                    output_field=models.BooleanField(),
                ),
            ),
            default=None,
        ),
        output_field=models.BooleanField(null=True),
        db_persist=True,
    )

    value_str = models.GeneratedField(
        expression=Case(
            When(value_jsonb__t="str", then=KeyTextTransform("v", "value_jsonb")),
            default=None,
        ),
        output_field=models.TextField(null=True),
        db_persist=True,
    )

    ts = models.DateTimeField(default=timezone.now, null=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    def formatted_value(self, precision: int = 3) -> str:
        """
        Returns telemetry value formatted for UI/exports.
        """
        if self.value_numeric is not None:
            return f"{self.value_numeric:.{precision}f}"
        if self.value_bool is not None:
            return str(self.value_bool)
        if self.value_str is not None:
            return self.value_str
        return ""

    def formatted_value_with_type(self, precision: int = 3) -> str:
        """
        Returns telemetry value formatted with type label (admin list display).
        """
        if self.value_numeric is not None:
            return f"{self.value_numeric:.{precision}f} (numeric)"
        if self.value_bool is not None:
            return f"{self.value_bool} (bool)"
        if self.value_str is not None:
            return f"{self.value_str} (str)"
        return ""

    class Meta:
        db_table = "telemetries"
        indexes = [
            models.Index(
                fields=["device_metric", "ts"], name="idx_telemetries_metric_time"
            ),
            models.Index(fields=["ts"], name="idx_telemetries_timestamp"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["device_metric", "ts"], name="unique_telemetry_per_metric_time"
            ),
        ]
