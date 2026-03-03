from django.db import models


class MetricDataType(models.TextChoices):
    NUMERIC = 'numeric', 'Numeric'
    BOOLEAN = 'bool', 'Boolean'
    STRING = 'str', 'String'


class Metric(models.Model):
    id = models.AutoField(primary_key=True)
    metric_type = models.CharField(
        max_length=100, null=False, db_collation='case_insensitive', db_index=True
    )
    unit = models.CharField(
        max_length=10, null=False, db_collation='case_insensitive', db_index=True
    )
    data_type = models.CharField(
        max_length=10, choices=MetricDataType.choices, default=MetricDataType.NUMERIC
    )

    class Meta:
        db_table = 'metrics'
        constraints = [
            models.UniqueConstraint(
                fields=['metric_type', 'unit'],
                name='unique_metric_type_with_unit',
            ),
            models.CheckConstraint(
                condition=models.Q(data_type__in=MetricDataType.values),
                name="check_valid_metric_data_type",
            ),
        ]

    def __str__(self):
        return f"{self.metric_type}"
