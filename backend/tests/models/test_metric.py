"""Unit tests for Metric model."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.devices.models import Metric
from apps.devices.models.metric import MetricDataType
from tests.fixtures.factories import MetricFactory


pytestmark = pytest.mark.django_db


class TestMetricCreation:
    """Tests for Metric model creation and field validation."""

    def test_create_numeric_metric(self):
        """Test creating a metric with numeric data type."""
        metric = MetricFactory(metric_type="temperature", data_type="numeric")

        assert metric.id is not None
        assert metric.metric_type == "temperature"
        assert metric.data_type == "numeric"

    def test_create_boolean_metric(self):
        """Test creating a metric with boolean data type."""
        metric = MetricFactory(metric_type="is_online", data_type="bool")

        assert metric.data_type == "bool"

    def test_create_string_metric(self):
        """Test creating a metric with string data type."""
        metric = MetricFactory(metric_type="status", data_type="str")

        assert metric.data_type == "str"

    def test_default_data_type_is_numeric(self):
        """Test that default data_type is numeric."""
        metric = Metric.objects.create(metric_type="test_default")

        assert metric.data_type == MetricDataType.NUMERIC


class TestMetricValidation:
    """Tests for Metric model validation rules."""

    def test_metric_type_required(self):
        """Test that metric_type is required."""
        metric = Metric(metric_type=None, data_type="numeric")

        with pytest.raises(ValidationError) as exc:
            metric.full_clean()

        assert "metric_type" in exc.value.message_dict

    def test_data_type_required(self):
        """Test that data_type is required."""
        metric = Metric(metric_type="test_metric", data_type=None)

        with pytest.raises(ValidationError) as exc:
            metric.full_clean()

        assert "data_type" in exc.value.message_dict

    def test_metric_type_unique(self):
        """Test that metric_type must be unique."""
        MetricFactory(metric_type="humidity")

        with pytest.raises(IntegrityError):
            MetricFactory(metric_type="humidity")

    def test_invalid_data_type_rejected(self):
        """Test that invalid data_type raises validation error."""
        metric = Metric(metric_type="test", data_type="INVALID")

        with pytest.raises(ValidationError) as exc:
            metric.full_clean()

        assert "data_type" in exc.value.message_dict

    def test_data_type_choices(self):
        """Test that MetricDataType has correct values."""
        assert MetricDataType.NUMERIC == "numeric"
        assert MetricDataType.BOOLEAN == "bool"
        assert MetricDataType.STRING == "str"


class TestMetricStrMethod:
    """Tests for Metric __str__ method."""

    def test_str_returns_metric_type(self):
        """Test __str__ returns metric_type."""
        metric = MetricFactory(metric_type="pressure")

        assert str(metric) == "pressure"
