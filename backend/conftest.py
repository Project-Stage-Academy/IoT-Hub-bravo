"""
Pytest configuration and shared fixtures for the IoT Hub test suite.

This module provides reusable fixtures for:
- Database access and test client
- User fixtures (admin, staff, regular users)
- Device, Metric, DeviceMetric fixtures
- Telemetry, Rule, Event fixtures
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
# User Fixtures
# =============================================================================


@pytest.fixture
def superuser(db):
    """Create a superuser for admin tests."""
    from apps.users.models import User

    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user (non-superuser)."""
    from apps.users.models import User

    user = User.objects.create_user(
        email="staff@example.com",
        password="staffpass123",
        first_name="Staff",
        last_name="User",
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user (client role)."""
    from apps.users.models import User

    return User.objects.create_user(
        email="user@example.com",
        password="userpass123",
        first_name="Regular",
        last_name="User",
    )


@pytest.fixture
def authenticated_client(client, regular_user):
    """Django test client logged in as regular user."""
    client.login(email="user@example.com", password="userpass123")
    return client


@pytest.fixture
def admin_client(client, superuser):
    """Django test client logged in as superuser."""
    client.login(email="admin@example.com", password="adminpass123")
    return client


# =============================================================================
# Device Fixtures
# =============================================================================


@pytest.fixture
def metric(db):
    """Create a basic numeric metric."""
    from apps.devices.models import Metric

    return Metric.objects.create(
        metric_type="temperature",
        data_type="NUMERIC",
    )


@pytest.fixture
def metric_boolean(db):
    """Create a boolean metric."""
    from apps.devices.models import Metric

    return Metric.objects.create(
        metric_type="is_online",
        data_type="BOOLEAN",
    )


@pytest.fixture
def metric_string(db):
    """Create a string metric."""
    from apps.devices.models import Metric

    return Metric.objects.create(
        metric_type="status_message",
        data_type="STRING",
    )


@pytest.fixture
def device(db, regular_user):
    """Create a basic device."""
    from apps.devices.models import Device

    return Device.objects.create(
        serial_id="TEST-001",
        name="Test Device",
        description="A test device",
        user=regular_user,
        is_active=True,
    )


@pytest.fixture
def inactive_device(db, regular_user):
    """Create an inactive device."""
    from apps.devices.models import Device

    return Device.objects.create(
        serial_id="TEST-002",
        name="Inactive Device",
        description="An inactive test device",
        user=regular_user,
        is_active=False,
    )


@pytest.fixture
def device_metric(db, device, metric):
    """Create a device-metric relationship."""
    from apps.devices.models import DeviceMetric

    return DeviceMetric.objects.create(
        device=device,
        metric=metric,
    )


# =============================================================================
# Telemetry Fixtures
# =============================================================================


@pytest.fixture
def telemetry(db, device_metric):
    """Create a single telemetry record with numeric value."""
    from apps.devices.models import Telemetry

    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"value": 25.5},
    )


@pytest.fixture
def telemetry_batch(db, device_metric):
    """Create a batch of telemetry records."""
    from apps.devices.models import Telemetry

    records = []
    for i in range(5):
        records.append(
            Telemetry.objects.create(
                device_metric=device_metric,
                value_jsonb={"value": 20.0 + i},
            )
        )
    return records


# =============================================================================
# Rule and Event Fixtures
# =============================================================================


@pytest.fixture
def rule(db, device_metric):
    """Create a basic threshold rule."""
    from apps.rules.models import Rule

    return Rule.objects.create(
        name="High Temperature Alert",
        description="Alert when temperature exceeds 30°C",
        condition={"type": "threshold", "operator": ">", "value": 30},
        action={"type": "notify", "channel": "email"},
        device_metric=device_metric,
        is_active=True,
    )


@pytest.fixture
def inactive_rule(db, device_metric):
    """Create an inactive rule."""
    from apps.rules.models import Rule

    return Rule.objects.create(
        name="Disabled Rule",
        description="This rule is disabled",
        condition={"type": "threshold", "operator": "<", "value": 10},
        action={"type": "notify", "channel": "sms"},
        device_metric=device_metric,
        is_active=False,
    )


@pytest.fixture
def event(db, rule):
    """Create a single event."""
    from apps.rules.models import Event

    return Event.objects.create(
        rule=rule,
        acknowledged=False,
    )


@pytest.fixture
def acknowledged_event(db, rule):
    """Create an acknowledged event."""
    from apps.rules.models import Event

    return Event.objects.create(
        rule=rule,
        acknowledged=True,
    )
