import pytest

from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_superuser(
        username="test_admin",
        email="test_admin@example.com",
        password="testpass123",
    )


@pytest.fixture
def staff_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="test_regular",
        email="test_regular@example.com",
        password="testpass123",
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def device(staff_user):
    return Device.objects.create(
        serial_id="SN-SMOKE-001",
        name="Smoke Test Device",
        description="Device for smoke testing",
        user=staff_user,
        is_active=True,
    )


@pytest.fixture
def metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric(device, metric):
    return DeviceMetric.objects.create(device=device, metric=metric)


@pytest.fixture
def telemetry(device_metric):
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": "25.5"},
    )


@pytest.fixture
def rule(device_metric):
    return Rule.objects.create(
        name="Smoke Test Rule",
        description="Rule for smoke testing",
        device_metric=device_metric,
        condition={"type": "threshold", "value": 30},
        action={"type": "log", "message": "Test"},
        is_active=True,
    )


@pytest.fixture
def event(rule):
    return Event.objects.create(rule=rule)


@pytest.fixture
def logged_in_client(client, superuser):
    """
    Logs in before each test (analog of a setUp()).
    """
    ok = client.login(username="test_admin", password="testpass123")
    assert ok is True
    return client


@pytest.mark.django_db
def test_admin_login_page_loads(client):
    resp = client.get("/admin/login/")
    assert resp.status_code == 200
    assert "Django administration" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_admin_login_success(client, superuser):
    resp = client.post(
        "/admin/login/",
        {"username": "test_admin", "password": "testpass123", "next": "/admin/"},
        follow=False,
    )
    assert resp.status_code == 302
    assert "/admin/" in resp["Location"]


@pytest.mark.django_db
def test_admin_index_page_loads(logged_in_client):
    resp = logged_in_client.get("/admin/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Site administration" in body
    assert "Devices" in body
    assert "Users" in body


@pytest.mark.django_db
def test_devices_list_page_loads(logged_in_client, device):
    resp = logged_in_client.get("/admin/devices/device/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Select device to change" in body
    assert "Smoke Test Device" in body


@pytest.mark.django_db
def test_device_detail_page_loads(logged_in_client, device):
    resp = logged_in_client.get(f"/admin/devices/device/{device.id}/change/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "SN-SMOKE-001" in body
    assert "Smoke Test Device" in body


@pytest.mark.django_db
def test_device_add_page_loads(logged_in_client):
    resp = logged_in_client.get("/admin/devices/device/add/")
    assert resp.status_code == 200
    assert "Add device" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_telemetry_list_page_loads(logged_in_client, telemetry):
    resp = logged_in_client.get("/admin/devices/telemetry/")
    assert resp.status_code == 200
    assert "Select telemetry to change" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_telemetry_detail_page_loads(logged_in_client, telemetry):
    resp = logged_in_client.get(f"/admin/devices/telemetry/{telemetry.id}/change/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_metrics_list_page_loads(logged_in_client, metric):
    resp = logged_in_client.get("/admin/devices/metric/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Select metric to change" in body
    assert "temperature" in body


@pytest.mark.django_db
def test_device_metrics_list_page_loads(logged_in_client, device_metric):
    resp = logged_in_client.get("/admin/devices/devicemetric/")
    assert resp.status_code == 200
    assert "Select device metric to change" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_rules_list_page_loads(logged_in_client, rule):
    resp = logged_in_client.get("/admin/rules/rule/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Select rule to change" in body
    assert "Smoke Test Rule" in body


@pytest.mark.django_db
def test_rule_detail_page_loads(logged_in_client, rule):
    resp = logged_in_client.get(f"/admin/rules/rule/{rule.id}/change/")
    assert resp.status_code == 200
    assert "Smoke Test Rule" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_rule_add_page_loads(logged_in_client):
    resp = logged_in_client.get("/admin/rules/rule/add/")
    assert resp.status_code == 200
    assert "Add rule" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_events_list_page_loads(logged_in_client, event):
    resp = logged_in_client.get("/admin/rules/event/")
    assert resp.status_code == 200
    assert "Select event to change" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_event_detail_page_loads(logged_in_client, event):
    resp = logged_in_client.get(f"/admin/rules/event/{event.id}/change/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_users_list_page_loads(logged_in_client):
    resp = logged_in_client.get("/admin/users/user/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Select user to change" in body
    assert "test_admin" in body


@pytest.mark.django_db
def test_admin_logout_works(logged_in_client):
    resp = logged_in_client.post("/admin/logout/")
    assert resp.status_code == 200
    assert "Logged out" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_device_search_works(logged_in_client, device):
    resp = logged_in_client.get("/admin/devices/device/?q=SMOKE")
    assert resp.status_code == 200
    assert "Smoke Test Device" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_device_filter_by_active_works(logged_in_client, device):
    resp = logged_in_client.get("/admin/devices/device/?is_active__exact=1")
    assert resp.status_code == 200
    assert "Smoke Test Device" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_device_enable_action_works(logged_in_client, device):
    device.is_active = False
    device.save(update_fields=["is_active"])

    resp = logged_in_client.post(
        "/admin/devices/device/",
        {"action": "enable_devices", "_selected_action": [str(device.id)]},
        follow=False,
    )
    # Admin actions usually redirect back to the changelist
    assert resp.status_code in (302, 200)

    device.refresh_from_db()
    assert device.is_active is True


@pytest.mark.django_db
def test_non_staff_user_cannot_access_admin(client, django_user_model):
    django_user_model.objects.create_user(
        username="regular_user",
        email="regular@example.com",
        password="testpass123",
    )
    ok = client.login(username="regular_user", password="testpass123")
    assert ok is True

    resp = client.get("/admin/", follow=False)
    assert resp.status_code == 302
    assert "/admin/login/" in resp["Location"]


@pytest.mark.django_db
def test_anonymous_user_redirected_to_login(client):
    resp = client.get("/admin/", follow=False)
    assert resp.status_code == 302
    assert "/admin/login/" in resp["Location"]
