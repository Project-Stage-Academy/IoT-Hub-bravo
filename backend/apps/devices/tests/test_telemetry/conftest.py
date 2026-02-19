from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
import pytest

from apps.devices.models import Device, Metric, DeviceMetric

User = get_user_model()


@pytest.fixture
def valid_telemetry_payload():
    return {
        'schema_version': 1,
        'device': 'DEV-001',
        'metrics': {
            'temperature': {
                'value': 21.5,
                'unit': "celsius",
            },
            'door_open': {
                'value': False,
                'unit': "open",
            },
            'status': {
                'value': "ok",
                'unit': "Online",
            },
        },
        'ts': '2026-02-04T12:00:00Z',
    }


@pytest.fixture
def ts():
    return timezone.now()


@pytest.fixture
def user(db):
    return User.objects.create(username='test-user', email='test@example.com')


@pytest.fixture
def active_device(db, user):
    return Device.objects.create(serial_id='DEV-001', is_active=True, user=user)


@pytest.fixture
def inactive_device(db, user):
    return Device.objects.create(serial_id='DEV-002', is_active=False, user=user)


@pytest.fixture
def metric_temperature_numeric(db):
    return Metric.objects.create(metric_type='temperature', data_type='numeric')


@pytest.fixture
def metric_door_open_bool(db):
    return Metric.objects.create(metric_type='door_open', data_type='bool')


@pytest.fixture
def metric_status_str(db):
    return Metric.objects.create(metric_type='status', data_type='str')


@pytest.fixture
def device_metric_numeric(db, active_device, metric_temperature_numeric):
    return DeviceMetric.objects.create(device=active_device, metric=metric_temperature_numeric)


@pytest.fixture
def device_metric_bool(db, active_device, metric_door_open_bool):
    return DeviceMetric.objects.create(device=active_device, metric=metric_door_open_bool)


@pytest.fixture
def device_metric_str(db, active_device, metric_status_str):
    return DeviceMetric.objects.create(device=active_device, metric=metric_status_str)


@pytest.fixture
def telemetry_ingest_url():
    return reverse('ingest-telemetry')
