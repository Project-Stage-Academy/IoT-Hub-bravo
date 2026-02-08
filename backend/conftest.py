"""
Pytest configuration and shared fixtures for the IoT Hub test suite.

This module provides reusable fixtures using factory_boy factories.
"""

import os
import django
import pytest
from django.conf import settings
from django.test import Client


def pytest_configure():
    """Configure Django settings before tests run."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

    if not settings.configured:
        django.setup()


# =============================================================================
# Database and Client Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """HTTP test client for API endpoint testing."""
    return Client()


# =============================================================================
# User Fixtures (using factories)
# =============================================================================


@pytest.fixture
def regular_user(db):
    """Create a regular user (client role)."""
    from tests.fixtures.factories import UserFactory

    return UserFactory(password="testpass123")


@pytest.fixture
def staff_user(db):
    """Create a staff user (non-superuser)."""
    from tests.fixtures.factories import StaffUserFactory

    return StaffUserFactory(password="testpass123")


@pytest.fixture
def superuser(db):
    """Create a superuser for admin tests."""
    from tests.fixtures.factories import AdminUserFactory

    return AdminUserFactory(password="adminpass123")


@pytest.fixture
def authenticated_client(client, regular_user):
    """Django test client logged in as regular user."""
    client.login(username=regular_user.username, password="testpass123")
    return client


@pytest.fixture
def admin_client(client, superuser):
    """Django test client logged in as superuser."""
    client.login(username=superuser.username, password="adminpass123")
    return client


# =============================================================================
# Device Fixtures (using factories)
# =============================================================================


@pytest.fixture
def metric(db):
    """Create a basic numeric metric."""
    from tests.fixtures.factories import MetricFactory

    return MetricFactory(metric_type="temperature", data_type="NUMERIC")


@pytest.fixture
def metric_boolean(db):
    """Create a boolean metric."""
    from tests.fixtures.factories import BooleanMetricFactory

    return BooleanMetricFactory(metric_type="is_online")


@pytest.fixture
def metric_string(db):
    """Create a string metric."""
    from tests.fixtures.factories import StringMetricFactory

    return StringMetricFactory(metric_type="status_message")


@pytest.fixture
def device(db, regular_user):
    """Create a basic device."""
    from tests.fixtures.factories import DeviceFactory

    return DeviceFactory(
        serial_id="TEST-001",
        name="Test Device",
        user=regular_user,
    )


@pytest.fixture
def inactive_device(db, regular_user):
    """Create an inactive device."""
    from tests.fixtures.factories import InactiveDeviceFactory

    return InactiveDeviceFactory(
        serial_id="TEST-002",
        name="Inactive Device",
        user=regular_user,
    )


@pytest.fixture
def device_metric(db, device, metric):
    """Create a device-metric relationship."""
    from tests.fixtures.factories import DeviceMetricFactory

    return DeviceMetricFactory(device=device, metric=metric)


# =============================================================================
# Telemetry Fixtures (using factories)
# =============================================================================


@pytest.fixture
def telemetry(db, device_metric):
    """Create a single telemetry record with numeric value."""
    from tests.fixtures.factories import TelemetryFactory

    return TelemetryFactory(
        device_metric=device_metric,
        value_jsonb={"value": 25.5},
    )


@pytest.fixture
def telemetry_batch(db, device_metric):
    """Create a batch of telemetry records."""
    from tests.fixtures.factories import TelemetryFactory

    return TelemetryFactory.create_batch(5, device_metric=device_metric)


# =============================================================================
# Rule and Event Fixtures (using factories)
# =============================================================================


@pytest.fixture
def rule(db, device_metric):
    """Create a basic threshold rule."""
    from tests.fixtures.factories import RuleFactory

    return RuleFactory(
        name="High Temperature Alert",
        device_metric=device_metric,
    )


@pytest.fixture
def inactive_rule(db, device_metric):
    """Create an inactive rule."""
    from tests.fixtures.factories import InactiveRuleFactory

    return InactiveRuleFactory(
        name="Disabled Rule",
        device_metric=device_metric,
    )


@pytest.fixture
def event(db, rule):
    """Create a single event."""
    from tests.fixtures.factories import EventFactory

    return EventFactory(rule=rule)


@pytest.fixture
def acknowledged_event(db, rule):
    """Create an acknowledged event."""
    from tests.fixtures.factories import AcknowledgedEventFactory

    return AcknowledgedEventFactory(rule=rule)
