"""Unit tests for DeviceMetric model."""

import pytest
from django.db import IntegrityError

from apps.devices.models import DeviceMetric
from tests.fixtures.factories import (
    DeviceFactory,
    MetricFactory,
    DeviceMetricFactory,
)


pytestmark = pytest.mark.django_db


class TestDeviceMetricCreation:
    """Tests for DeviceMetric model creation."""

    def test_create_device_metric(self):
        """Test creating a device-metric relationship."""
        device_metric = DeviceMetricFactory()

        assert device_metric.id is not None
        assert device_metric.device is not None
        assert device_metric.metric is not None

    def test_create_with_specific_device_and_metric(self):
        """Test creating device_metric with specific device and metric."""
        device = DeviceFactory(name="Sensor A")
        metric = MetricFactory(metric_type="humidity")

        device_metric = DeviceMetricFactory(device=device, metric=metric)

        assert device_metric.device.name == "Sensor A"
        assert device_metric.metric.metric_type == "humidity"


class TestDeviceMetricConstraints:
    """Tests for DeviceMetric model constraints."""

    def test_device_metric_unique_together(self):
        """Test that device-metric combination must be unique."""
        device = DeviceFactory()
        metric = MetricFactory()

        DeviceMetricFactory(device=device, metric=metric)

        with pytest.raises(IntegrityError):
            DeviceMetricFactory(device=device, metric=metric)

    def test_same_device_different_metrics_allowed(self):
        """Test that same device can have different metrics."""
        device = DeviceFactory()
        metric1 = MetricFactory(metric_type="temperature")
        metric2 = MetricFactory(metric_type="humidity")

        dm1 = DeviceMetricFactory(device=device, metric=metric1)
        dm2 = DeviceMetricFactory(device=device, metric=metric2)

        assert dm1.device == dm2.device
        assert dm1.metric != dm2.metric

    def test_same_metric_different_devices_allowed(self):
        """Test that same metric can be used by different devices."""
        device1 = DeviceFactory(serial_id="SN-001")
        device2 = DeviceFactory(serial_id="SN-002")
        metric = MetricFactory()

        dm1 = DeviceMetricFactory(device=device1, metric=metric)
        dm2 = DeviceMetricFactory(device=device2, metric=metric)

        assert dm1.metric == dm2.metric
        assert dm1.device != dm2.device


class TestDeviceMetricRelationships:
    """Tests for DeviceMetric foreign key behavior."""

    def test_cascade_delete_on_device(self):
        """Test that deleting device cascades to device_metric."""
        device_metric = DeviceMetricFactory()
        device_id = device_metric.device.id
        device_metric_id = device_metric.id

        device_metric.device.delete()

        assert not DeviceMetric.objects.filter(id=device_metric_id).exists()

    def test_restrict_delete_on_metric(self):
        """Test that deleting metric is restricted if device_metric exists."""
        device_metric = DeviceMetricFactory()
        metric = device_metric.metric

        with pytest.raises(IntegrityError):
            metric.delete()


class TestDeviceMetricStrMethod:
    """Tests for DeviceMetric __str__ method."""

    def test_str_returns_device_name_and_metric_type(self):
        """Test __str__ returns 'device.name - metric.metric_type'."""
        device = DeviceFactory(name="Weather Station")
        metric = MetricFactory(metric_type="temperature")
        device_metric = DeviceMetricFactory(device=device, metric=metric)

        assert str(device_metric) == "Weather Station - temperature"
