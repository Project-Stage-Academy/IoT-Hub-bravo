# tests/test_device.py
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


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", email="admin@example.com", password="password123", role="admin"
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="client", email="client@example.com", password="password123", role="client"
    )


@pytest.fixture
def admin_token(admin_user):
    payload = {"sub": admin_user.id, "role": "admin"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
def client_token(client_user):
    payload = {"sub": client_user.id, "role": "client"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
def auth_headers(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def device_active(client_user):
    return Device.objects.create(
        serial_id="SN-123", name="Active Device", user=client_user, is_active=True
    )


@pytest.fixture
def device_inactive(client_user):
    return Device.objects.create(
        serial_id="SN-999", name="Inactive Device", user=client_user, is_active=False
    )


@pytest.fixture
def valid_device(client_user):
    return Device(serial_id="SN-123", name="Active Device", user=client_user, is_active=True)


@pytest.fixture
def invalid_device():
    return Device(name="Invalid Device", user=None, is_active=True)


# Model validation


# Testing device creation with valid data
@pytest.mark.django_db
def test_device_model_valid(client_user):
    device = Device(
        serial_id="SERIAL-123",
        name="Test Device",
        description="Some description",
        user=client_user,
        is_active=True,
    )

    device.full_clean()


# Testing device creation without serial_id
@pytest.mark.django_db
def test_device_serial_id_required(client_user):
    device = Device(
        serial_id=None,
        name="Device",
        user=client_user,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "serial_id" in exc.value.message_dict


# Testing device creation without name
@pytest.mark.django_db
def test_device_name_required(client_user):
    device = Device(
        serial_id="SER-1",
        name=None,
        user=client_user,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "name" in exc.value.message_dict


# Testing device creation without user
@pytest.mark.django_db
def test_device_user_required():
    device = Device(
        serial_id="SER-2",
        name="Device without user",
        user=None,
    )

    with pytest.raises(ValidationError) as exc:
        device.full_clean()

    assert "user" in exc.value.message_dict


# Testing devices creation with same serial_id
@pytest.mark.django_db
def test_device_serial_id_unique(client_user):
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


# Testing device creation without description
@pytest.mark.django_db
def test_device_description_optional(client_user):
    device = Device(
        serial_id="SER-4",
        name="Device",
        description=None,
        user=client_user,
    )

    device.full_clean()


# Serializer behavior


# Validating device with valid data
def test_device_serializer_valid_data():
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


# Validating device with missing fields: serial_id, name, user_id
def test_device_serializer_missing_required_fields():
    serializer = DeviceCreateV1Serializer(data={})

    assert serializer.is_valid() is False

    assert "serial_id" in serializer.errors
    assert "name" in serializer.errors
    assert "user_id" in serializer.errors


# Validating device data with wrong DataType
def test_device_serializer_invalid_field_types():
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

    assert serializer.errors["serial_id"] == "'serial_id' must be a valid value."
    assert serializer.errors["name"] == "'name' must be a valid value."
    assert serializer.errors["description"] == "'description' must be a valid value."
    assert serializer.errors["user_id"] == "'user_id' must be a valid value."
    assert serializer.errors["is_active"] == "'is_active' must be a valid value."


# Validating device data for PATCH method (required fields are ignored)
def test_device_serializer_partial_update():
    serializer = DeviceCreateV1Serializer(data={"name": "Updated name"}, partial=True)

    assert serializer.is_valid() is True
    assert serializer.errors == {}
    assert serializer.validated_data == {"name": "Updated name"}


# Testing serialization method to_representation
@pytest.mark.django_db
def test_device_serializer_to_representation(client_user):
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


# API Endpoints testing


# client GET
@pytest.mark.django_db
def test_get_devices_as_client(client, client_user, client_token):
    Device.objects.create(serial_id="SER-1", name="D1", user=client_user)
    Device.objects.create(serial_id="SER-2", name="D2", user=client_user)

    response = client.get(
        "/api/devices/?limit=10&offset=0", **{"HTTP_AUTHORIZATION": f"Bearer {client_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


# unauthenticated GET
@pytest.mark.django_db
def test_get_devices_unauthenticated(client):
    response = client.get("/api/devices/?limit=10")
    assert response.status_code == 401
    assert "Authorization header required" in response.json()["error"]


# admin POST
@pytest.mark.django_db
def test_create_device_as_admin(client, admin_user, admin_token):
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
    response = client.post(
        "/api/devices/",
        data=json.dumps(payload),
        content_type="application/json",
        **{"HTTP_AUTHORIZATION": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["serial_id"] == "SER-100"


# client POST
@pytest.mark.django_db
def test_create_device_as_client_forbidden(client, client_user, client_token):
    payload = {
        "serial_id": "SER-101",
        "name": "Forbidden",
        "user_id": client_user.id,
    }

    response = client.post(
        "/api/devices/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {client_token}",
    )

    assert response.status_code == 403

    body = response.json()
    assert "error" in body
    assert body["error"] == "Permission denied"


# admin PATCH
@pytest.mark.django_db
def test_patch_device_as_admin(client, admin_user, admin_token):
    device = Device.objects.create(
        serial_id="SER-200",
        name="Old Name",
        user=admin_user,
        is_active=True,
    )

    payload = {"schema_version": "v1", "device": {"name": "Updated Name"}}

    response = client.patch(
        f"/api/devices/{device.id}/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {admin_token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Name"

    device.refresh_from_db()
    assert device.name == "Updated Name"


# admin DELETE
@pytest.mark.django_db
def test_delete_device_as_admin(client, admin_user, admin_token):
    device = Device.objects.create(serial_id="SER-300", name="ToDelete", user=admin_user)

    response = client.delete(
        f"/api/devices/{device.id}/", **{"HTTP_AUTHORIZATION": f"Bearer {admin_token}"}
    )

    assert response.status_code == 204
    assert not Device.objects.filter(id=device.id).exists()
