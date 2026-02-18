"""
Factory Boy factories for creating test data.

Usage in tests:
    from tests.fixtures.factories import DeviceFactory, TelemetryFactory

    # Create single instance
    device = DeviceFactory()

    # Create with custom fields
    device = DeviceFactory(name="Custom Name", is_active=False)

    # Create multiple instances
    devices = DeviceFactory.create_batch(10)

    # Build without saving to DB
    device = DeviceFactory.build()
"""

import random
import factory
from factory.django import DjangoModelFactory

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event

# =============================================================================
# User Factories
# =============================================================================


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    is_active = True
    role = "client"

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password after user creation."""
        if not create:
            return
        password = extracted or "testpass123"
        obj.set_password(password)
        obj.save()


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    email = factory.Sequence(lambda n: f"admin{n}@example.com")
    username = factory.Sequence(lambda n: f"admin{n}")
    role = "admin"
    is_staff = True
    is_superuser = True


class StaffUserFactory(UserFactory):
    """Factory for creating staff users (non-superuser)."""

    email = factory.Sequence(lambda n: f"staff{n}@example.com")
    username = factory.Sequence(lambda n: f"staff{n}")
    is_staff = True


# =============================================================================
# Device Factories
# =============================================================================


class MetricFactory(DjangoModelFactory):
    """Factory for creating Metric instances."""

    class Meta:
        model = Metric

    metric_type = factory.Sequence(lambda n: f"metric_{n}")
    data_type = "numeric"


class BooleanMetricFactory(MetricFactory):
    """Factory for creating boolean metrics."""

    metric_type = factory.Sequence(lambda n: f"bool_metric_{n}")
    data_type = "bool"


class StringMetricFactory(MetricFactory):
    """Factory for creating string metrics."""

    metric_type = factory.Sequence(lambda n: f"str_metric_{n}")
    data_type = "str"


class DeviceFactory(DjangoModelFactory):
    """Factory for creating Device instances."""

    class Meta:
        model = Device

    serial_id = factory.Sequence(lambda n: f"SN-{n:05d}")
    name = factory.Sequence(lambda n: f"Device {n}")
    description = factory.Faker("sentence", nb_words=6)
    user = factory.SubFactory(UserFactory)
    is_active = True


class InactiveDeviceFactory(DeviceFactory):
    """Factory for creating inactive devices."""

    is_active = False


class DeviceMetricFactory(DjangoModelFactory):
    """Factory for creating DeviceMetric instances."""

    class Meta:
        model = DeviceMetric

    device = factory.SubFactory(DeviceFactory)
    metric = factory.SubFactory(MetricFactory)


# =============================================================================
# Telemetry Factories
# =============================================================================


class TelemetryFactory(DjangoModelFactory):
    """Factory for creating Telemetry instances with numeric value."""

    class Meta:
        model = Telemetry

    device_metric = factory.SubFactory(DeviceMetricFactory)
    value_jsonb = factory.LazyFunction(lambda: {"t": "numeric", "v": "25.5"})


class TelemetryNumericFactory(TelemetryFactory):
    """Factory for telemetry with random numeric values."""

    value_jsonb = factory.LazyFunction(
        lambda: {
            "t": "numeric",
            "v": str(round(random.uniform(0, 100), 2)),
        }
    )


class TelemetryBooleanFactory(TelemetryFactory):
    """Factory for telemetry with boolean values."""

    device_metric = factory.SubFactory(
        DeviceMetricFactory,
        metric=factory.SubFactory(BooleanMetricFactory),
    )
    value_jsonb = factory.LazyFunction(lambda: {"t": "bool", "v": "true"})


class TelemetryStringFactory(TelemetryFactory):
    """Factory for telemetry with string values."""

    device_metric = factory.SubFactory(
        DeviceMetricFactory,
        metric=factory.SubFactory(StringMetricFactory),
    )
    value_jsonb = factory.LazyFunction(lambda: {"t": "str", "v": "status_ok"})


# =============================================================================
# Rule and Event Factories
# =============================================================================


class RuleFactory(DjangoModelFactory):
    """Factory for creating Rule instances."""

    class Meta:
        model = Rule

    name = factory.Sequence(lambda n: f"Rule {n}")
    description = factory.Faker("sentence", nb_words=8)
    condition = factory.LazyFunction(lambda: {"type": "threshold", "operator": ">", "value": 30})
    action = factory.LazyFunction(lambda: {"type": "notify", "channel": "email"})
    device_metric = factory.SubFactory(DeviceMetricFactory)
    is_active = True


class InactiveRuleFactory(RuleFactory):
    """Factory for creating inactive rules."""

    is_active = False


class EventFactory(DjangoModelFactory):
    """Factory for creating Event instances."""

    class Meta:
        model = Event

    rule = factory.SubFactory(RuleFactory)
    acknowledged = False


class AcknowledgedEventFactory(EventFactory):
    """Factory for creating acknowledged events."""

    acknowledged = True
