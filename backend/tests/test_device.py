# tests/test_device.py
import pytest
from rest_framework.test import APIClient
from apps.devices.models import Device
from apps.devices.serializers.device_serializer import DeviceSerializer
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user1():
    return User.objects.create(username="user1", email="user1@example.com", role="client")

@pytest.fixture
def user2():
    return User.objects.create(username="user2", email="user2@example.com", role="client")

@pytest.fixture
def device_active(user1):
    return Device.objects.create(
        serial_id="SN-123",
        name="Active Device",
        user=user1,
        is_active=True
    )

@pytest.fixture
def device_inactive(user2):
    return Device.objects.create(
        serial_id="SN-999",
        name="Inactive Device",
        user=user2,
        is_active=False
    )


def test_serializer_valid(device_active):
    serializer = DeviceSerializer(device_active)
    data = serializer.data
    assert data["serial_id"] == "SN-123"
    assert data["name"] == "Active Device"
    assert data["user"] == device_active.user.id
    assert data["is_active"] is True

def test_serializer_invalid():
    invalid_data = {
        "serial_id": "",
        "name": "",
        "user": 999
    }
    serializer = DeviceSerializer(data=invalid_data)
    assert not serializer.is_valid()
    errors = serializer.errors
    assert "serial_id" in errors
    assert "name" in errors
    assert "user" in errors


def test_api_list_devices(api_client, device_active, device_inactive):
    response = api_client.get("/api/devices/")
    assert response.status_code == 200

    active_ids = [d["id"] for d in response.data if d["is_active"]]
    assert device_active.id in active_ids

    inactive_ids = [d["id"] for d in response.data if not d["is_active"]]
    assert device_inactive.id in inactive_ids


def test_api_create_device_valid(api_client, user1):
    payload = {
        "serial_id": "SN-777",
        "name": "New Device",
        "user": user1.id
    }
    response = api_client.post("/api/devices/", payload, format="json")
    assert response.status_code == 201
    data = response.data
    assert data["serial_id"] == "SN-777"
    assert data["name"] == "New Device"
    assert data["user"] == user1.id
    assert data["is_active"] is True

def test_api_create_device_invalid(api_client):
    payload = {
        "serial_id": "",
        "name": "",
        "user": 999
    }
    response = api_client.post("/api/devices/", payload, format="json")
    assert response.status_code == 400
    errors = response.data
    assert "serial_id" in errors
    assert "name" in errors
    assert "user" in errors

def test_api_retrieve_device(api_client, device_active):
    url = f"/api/devices/{device_active.id}/"
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.data
    assert data["id"] == device_active.id
    assert data["name"] == device_active.name

def test_api_update_device(api_client, device_active):
    url = f"/api/devices/{device_active.id}/"
    payload = {"name": "Updated Device"}
    response = api_client.patch(url, payload, format="json")
    assert response.status_code == 200
    device_active.refresh_from_db()
    assert device_active.name == "Updated Device"

def test_api_delete_device(api_client, device_active):
    url = f"/api/devices/{device_active.id}/"
    response = api_client.delete(url)
    assert response.status_code == 204
    assert not Device.objects.filter(id=device_active.id).exists()
