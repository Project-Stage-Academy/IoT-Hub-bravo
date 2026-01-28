from django.db import models


class MetricDataType(models.TextChoices):
    NUMERIC = 'numeric', 'Numeric'
    BOOLEAN = 'bool', 'Boolean'
    STRING = 'str', 'String'


class Metric(models.Model):
    id = models.AutoField(primary_key=True)
    metric_type = models.CharField(
        max_length=100, unique=True, null=False, db_collation='case_insensitive'
    )
    data_type = models.CharField(
        max_length=10, choices=MetricDataType.choices, default=MetricDataType.NUMERIC
    )

    class Meta:
        db_table = 'metrics'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_type__in=MetricDataType.values),
                name="check_valid_device_metric_type",
            )
        ]

    def __str__(self):
        return self.metric_type
