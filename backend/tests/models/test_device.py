"""Unit tests for Device model, serializers, and API endpoints."""

import pytest
import jwt
import json

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.devices.models import Device
from apps.users.models import User
from apps.devices.serializers.device_serializers.base_device_serializer import (
    DeviceOutputSerializer,
)
from apps.devices.serializers.device_serializers.create_device_serializer import (
    DeviceCreateV1Serializer,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures (local to this test module)
# =============================================================================


@pytest.fixture
def client_user(db):
    """Create a client user for tests."""
    return User.objects.create_user(
        username="client", email="client@example.com", password="password123", role="client"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user for tests."""
    return User.objects.create_user(
        username="admin", email="admin@example.com", password="password123", role="admin"
    )


@pytest.fixture
def client_token(client_user):
    """Generate JWT token for client user."""
    payload = {"sub": client_user.id, "role": "client"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
def admin_token(admin_user):
    """Generate JWT token for admin user."""
    payload = {"sub": admin_user.id, "role": "admin"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
def auth_client(client, client_token):
    """Django test client with client auth headers."""
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {client_token}"
    return client


@pytest.fixture
def auth_admin_client(client, admin_token):
    """Django test client with admin auth headers."""
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {admin_token}"
    return client


# =============================================================================
# Model Validation Tests
# =============================================================================


def test_device_model_valid(client_user):
    """Test device creation with valid data."""
    device = Device(
        serial_id="SERIAL-123",
        name="Test Device",
        description="Some description",
        user=client_user,
        is_active=True,
    )
    device.full_clean()


def test_device_serial_id_required(client_user):
    """Test that serial_id is required."""
    device = Device(
        serial_id=None,
        name="Device",
        user=client_user,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "serial_id" in exc.value.message_dict


def test_device_name_required(client_user):
    """Test that name is required."""
    device = Device(
        serial_id="SER-1",
        name=None,
        user=client_user,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "name" in exc.value.message_dict


def test_device_user_required():
    """Test that user is required."""
    device = Device(
        serial_id="SER-2",
        name="Device without user",
        user=None,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "user" in exc.value.message_dict


def test_device_serial_id_unique(client_user):
    """Test that serial_id must be unique."""
    Device.objects.create(
        serial_id="UNIQUE-1",
        name="Device 1",
        user=client_user,
    )

    device = Device(
        serial_id="UNIQUE-1",
        name="Device 2",
        user=client_user,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "serial_id" in exc.value.message_dict


def test_device_description_optional(client_user):
    """Test that description is optional."""
    device = Device(
        serial_id="SER-4",
        name="Device",
        description=None,
        user=client_user,
    )
    device.full_clean()


# =============================================================================
# Serializer Tests
# =============================================================================


def test_device_serializer_valid_data():
    """Test serializer with valid data."""
    serializer = DeviceCreateV1Serializer(
        data={
            "serial_id": "SER-123",
            "name": "iPhone",
            "description": "Test device",
            "user_id": 1,
            "is_active": True,
        }
    )

    assert serializer.is_valid() is True
    assert serializer.errors == {}

    validated = serializer.validated_data
    assert validated == {
        "serial_id": "SER-123",
        "name": "iPhone",
        "description": "Test device",
        "user_id": 1,
        "is_active": True,
    }


def test_device_serializer_missing_required_fields():
    """Test serializer rejects missing required fields."""
    serializer = DeviceCreateV1Serializer(data={})

    assert serializer.is_valid() is False

    assert "serial_id" in serializer.errors
    assert "name" in serializer.errors
    assert "user_id" in serializer.errors


def test_device_serializer_invalid_field_types():
    """Test serializer rejects invalid field types."""
    serializer = DeviceCreateV1Serializer(
        data={
            "serial_id": 123,
            "name": True,
            "description": 999,
            "user_id": "1",
            "is_active": "yes",
        }
    )

    assert serializer.is_valid() is False

    # Check that errors exist for each field (don't check exact message text)
    assert "serial_id" in serializer.errors
    assert "name" in serializer.errors
    assert "description" in serializer.errors
    assert "user_id" in serializer.errors
    assert "is_active" in serializer.errors


def test_device_serializer_partial_update():
    """Test serializer with partial update (PATCH)."""
    serializer = DeviceCreateV1Serializer(data={"name": "Updated name"}, partial=True)

    assert serializer.is_valid() is True
    assert serializer.errors == {}
    assert serializer.validated_data == {"name": "Updated name"}


def test_device_serializer_to_representation(client_user):
    """Test serializer to_representation method."""
    device = Device.objects.create(
        serial_id="SER-999",
        name="MacBook",
        description="Laptop",
        user=client_user,
        is_active=True,
    )

    data = DeviceOutputSerializer.to_representation(instance=device)

    assert data == {
        "id": device.id,
        "serial_id": "SER-999",
        "name": "MacBook",
        "description": "Laptop",
        "user_id": client_user.id,
        "is_active": True,
        "created_at": device.created_at.isoformat(),
    }


# =============================================================================
# API Endpoint Tests
# =============================================================================


def test_get_devices_as_client(auth_client, client_user):
    """Test GET /api/devices/ as client user."""
    Device.objects.create(serial_id="SER-1", name="D1", user=client_user)
    Device.objects.create(serial_id="SER-2", name="D2", user=client_user)

    response = auth_client.get("/api/devices/?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_devices_unauthenticated(client):
    """Test GET /api/devices/ without authentication."""
    response = client.get("/api/devices/?limit=10")

    assert response.status_code == 401
    assert "error" in response.json()


def test_create_device_as_admin(auth_admin_client, admin_user):
    """Test POST /api/devices/ as admin user."""
    payload = {
        "schema_version": "v1",
        "device": {
            "serial_id": "SER-100",
            "name": "New Device",
            "description": None,
            "user_id": admin_user.id,
            "is_active": True,
        },
    }

    response = auth_admin_client.post(
        "/api/devices/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["serial_id"] == "SER-100"


def test_create_device_as_client_forbidden(auth_client, client_user):
    """Test POST /api/devices/ as client user (should be forbidden)."""
    payload = {
        "serial_id": "SER-101",
        "name": "Forbidden",
        "user_id": client_user.id,
    }

    response = auth_client.post(
        "/api/devices/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 403
    body = response.json()
    assert "error" in body


def test_patch_device_as_admin(auth_admin_client, admin_user):
    """Test PATCH /api/devices/{id}/ as admin user."""
    device = Device.objects.create(
        serial_id="SER-200",
        name="Old Name",
        user=admin_user,
        is_active=True,
    )

    payload = {"schema_version": "v1", "device": {"name": "Updated Name"}}

    response = auth_admin_client.patch(
        f"/api/devices/{device.id}/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Name"

    device.refresh_from_db()
    assert device.name == "Updated Name"


def test_delete_device_as_admin(auth_admin_client, admin_user):
    """Test DELETE /api/devices/{id}/ as admin user."""
    device = Device.objects.create(serial_id="SER-300", name="ToDelete", user=admin_user)

    response = auth_admin_client.delete(f"/api/devices/{device.id}/")

    assert response.status_code == 204
    assert not Device.objects.filter(id=device.id).exists()
