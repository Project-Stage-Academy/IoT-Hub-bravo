import json
import pytest
import jwt

from django.conf import settings
from django.utils import timezone

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric
from apps.rules.models import Rule, Event

pytestmark = pytest.mark.django_db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin_ev", email="admin_ev@example.com", password="pass123", role="admin"
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="client_ev", email="client_ev@example.com", password="pass123", role="client"
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
def device(client_user):
    return Device.objects.create(user=client_user, serial_id="EV-DEV-001", name="Event Device")


@pytest.fixture
def metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric(device, metric):
    return DeviceMetric.objects.create(device=device, metric=metric)


@pytest.fixture
def device2(client_user):
    return Device.objects.create(user=client_user, serial_id="EV-DEV-002", name="Event Device 2")


@pytest.fixture
def metric2():
    return Metric.objects.create(metric_type="humidity", data_type="numeric")


@pytest.fixture
def device_metric2(device2, metric2):
    return DeviceMetric.objects.create(device=device2, metric=metric2)


@pytest.fixture
def rule(device_metric):
    return Rule.objects.create(
        name="Temp Rule",
        device_metric=device_metric,
        condition={"type": "threshold", "operator": ">", "value": 50},
        action="notify",
        is_active=True,
    )


@pytest.fixture
def rule2(device_metric2):
    return Rule.objects.create(
        name="Humidity Rule",
        device_metric=device_metric2,
        condition={"type": "threshold", "operator": ">", "value": 80},
        action="notify",
        is_active=True,
    )


@pytest.fixture
def event(rule):
    return Event.objects.create(rule=rule)


@pytest.fixture
def event_acked(rule):
    return Event.objects.create(rule=rule, acknowledged=True)


# ============================================================================
# Helper
# ============================================================================


def auth(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ============================================================================
# GET /api/events/ — list
# ============================================================================


def test_list_events_returns_200_for_client(client, client_token, event):
    response = client.get("/api/events/", **auth(client_token))
    assert response.status_code == 200


def test_list_events_returns_200_for_admin(client, admin_token, event):
    response = client.get("/api/events/", **auth(admin_token))
    assert response.status_code == 200


def test_list_events_returns_401_without_token(client, event):
    response = client.get("/api/events/")
    assert response.status_code == 401


def test_list_events_response_shape(client, client_token, event):
    response = client.get("/api/events/", **auth(client_token))
    data = response.json()

    assert "count" in data
    assert "limit" in data
    assert "offset" in data
    assert "results" in data
    assert isinstance(data["results"], list)


def test_list_events_count_reflects_db(client, client_token, rule):
    Event.objects.create(rule=rule)
    Event.objects.create(rule=rule)
    Event.objects.create(rule=rule)

    response = client.get("/api/events/", **auth(client_token))
    data = response.json()

    assert data["count"] == 3


def test_list_events_result_item_fields(client, client_token, event):
    response = client.get("/api/events/", **auth(client_token))
    item = response.json()["results"][0]

    assert "id" in item
    assert "timestamp" in item
    assert "created_at" in item
    assert "acknowledged" in item
    assert "rule" in item
    assert "id" in item["rule"]
    assert "name" in item["rule"]
    assert "trigger_telemetry_id" in item
    assert "trigger_device_id" in item


def test_list_events_empty_when_no_events(client, client_token):
    response = client.get("/api/events/", **auth(client_token))
    data = response.json()
    assert data["count"] == 0
    assert data["results"] == []


def test_list_events_ordered_newest_first(client, client_token, rule):
    t1 = timezone.now()
    t2 = t1 + __import__("datetime").timedelta(seconds=10)
    e1 = Event.objects.create(rule=rule, timestamp=t1)
    e2 = Event.objects.create(rule=rule, timestamp=t2)

    response = client.get("/api/events/", **auth(client_token))
    ids = [r["id"] for r in response.json()["results"]]
    assert ids.index(e2.id) < ids.index(e1.id)


# ============================================================================
# GET /api/events/ — pagination
# ============================================================================


def test_list_events_limit_respected(client, client_token, rule):
    for _ in range(5):
        Event.objects.create(rule=rule)

    response = client.get("/api/events/?limit=2", **auth(client_token))
    data = response.json()

    assert data["count"] == 5
    assert len(data["results"]) == 2
    assert data["limit"] == 2


def test_list_events_offset_respected(client, client_token, rule):
    for _ in range(5):
        Event.objects.create(rule=rule)

    response = client.get("/api/events/?limit=10&offset=3", **auth(client_token))
    data = response.json()

    assert len(data["results"]) == 2  # 5 total, skip 3 → 2 remaining
    assert data["offset"] == 3


def test_list_events_default_limit_is_50(client, client_token, rule):
    response = client.get("/api/events/", **auth(client_token))
    assert response.json()["limit"] == 50


def test_list_events_returns_400_if_limit_exceeds_max(client, client_token):
    response = client.get("/api/events/?limit=201", **auth(client_token))
    assert response.status_code == 400
    assert "limit" in response.json()["errors"]


def test_list_events_returns_400_for_negative_offset(client, client_token):
    response = client.get("/api/events/?offset=-1", **auth(client_token))
    assert response.status_code == 400
    assert "offset" in response.json()["errors"]


def test_list_events_returns_400_for_non_integer_limit(client, client_token):
    response = client.get("/api/events/?limit=abc", **auth(client_token))
    assert response.status_code == 400
    assert "limit" in response.json()["errors"]


# ============================================================================
# GET /api/events/ — filter by rule_id
# ============================================================================


def test_filter_by_rule_id_returns_matching_events(client, client_token, rule, rule2):
    e1 = Event.objects.create(rule=rule)
    Event.objects.create(rule=rule2)

    response = client.get(f"/api/events/?rule_id={rule.id}", **auth(client_token))
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["id"] == e1.id


def test_filter_by_rule_id_returns_empty_for_unknown_rule(client, client_token):
    response = client.get("/api/events/?rule_id=99999", **auth(client_token))
    data = response.json()
    assert data["count"] == 0
    assert data["results"] == []


def test_filter_by_rule_id_returns_400_for_invalid_value(client, client_token):
    response = client.get("/api/events/?rule_id=abc", **auth(client_token))
    assert response.status_code == 400
    assert "rule_id" in response.json()["errors"]


# ============================================================================
# GET /api/events/ — filter by acknowledged
# ============================================================================


def test_filter_acknowledged_true(client, client_token, rule):
    Event.objects.create(rule=rule, acknowledged=False)
    Event.objects.create(rule=rule, acknowledged=True)

    response = client.get("/api/events/?acknowledged=true", **auth(client_token))
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["acknowledged"] is True


def test_filter_acknowledged_false(client, client_token, rule):
    Event.objects.create(rule=rule, acknowledged=False)
    Event.objects.create(rule=rule, acknowledged=True)

    response = client.get("/api/events/?acknowledged=false", **auth(client_token))
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["acknowledged"] is False


def test_filter_acknowledged_accepts_1_and_0(client, client_token, rule):
    Event.objects.create(rule=rule, acknowledged=True)
    Event.objects.create(rule=rule, acknowledged=False)

    r1 = client.get("/api/events/?acknowledged=1", **auth(client_token))
    assert r1.json()["count"] == 1

    r0 = client.get("/api/events/?acknowledged=0", **auth(client_token))
    assert r0.json()["count"] == 1


def test_filter_acknowledged_returns_400_for_invalid_value(client, client_token):
    response = client.get("/api/events/?acknowledged=maybe", **auth(client_token))
    assert response.status_code == 400
    assert "acknowledged" in response.json()["errors"]


# ============================================================================
# GET /api/events/ — filter by device_id
# ============================================================================


def test_filter_by_device_id(client, client_token, rule, device, device2, rule2):
    e1 = Event.objects.create(rule=rule, trigger_device_id=device.id)
    Event.objects.create(rule=rule2, trigger_device_id=device2.id)

    response = client.get(f"/api/events/?device_id={device.id}", **auth(client_token))
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["id"] == e1.id


def test_filter_by_device_id_returns_empty_for_unknown_device(client, client_token):
    response = client.get("/api/events/?device_id=99999", **auth(client_token))
    data = response.json()
    assert data["count"] == 0


# ============================================================================
# GET /api/events/ — combined filters
# ============================================================================


def test_combined_filter_rule_id_and_acknowledged(client, client_token, rule, rule2):
    Event.objects.create(rule=rule, acknowledged=True)
    Event.objects.create(rule=rule, acknowledged=False)
    Event.objects.create(rule=rule2, acknowledged=True)

    response = client.get(
        f"/api/events/?rule_id={rule.id}&acknowledged=true", **auth(client_token)
    )
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["rule"]["id"] == rule.id
    assert data["results"][0]["acknowledged"] is True


# ============================================================================
# GET /api/events/{id}/ — detail
# ============================================================================


def test_event_detail_returns_200(client, client_token, event):
    response = client.get(f"/api/events/{event.id}/", **auth(client_token))
    assert response.status_code == 200


def test_event_detail_returns_correct_event(client, client_token, event, rule):
    response = client.get(f"/api/events/{event.id}/", **auth(client_token))
    data = response.json()

    assert data["id"] == event.id
    assert data["acknowledged"] == event.acknowledged
    assert data["rule"]["id"] == rule.id
    assert data["rule"]["name"] == rule.name


def test_event_detail_returns_404_for_unknown_id(client, client_token):
    response = client.get("/api/events/99999/", **auth(client_token))
    assert response.status_code == 404
    assert "detail" in response.json()


def test_event_detail_returns_401_without_token(client, event):
    response = client.get(f"/api/events/{event.id}/")
    assert response.status_code == 401


def test_event_detail_returns_200_for_admin(client, admin_token, event):
    response = client.get(f"/api/events/{event.id}/", **auth(admin_token))
    assert response.status_code == 200


def test_event_detail_response_fields(client, client_token, event):
    response = client.get(f"/api/events/{event.id}/", **auth(client_token))
    data = response.json()

    assert "id" in data
    assert "timestamp" in data
    assert "created_at" in data
    assert "acknowledged" in data
    assert "rule" in data
    assert "trigger_telemetry_id" in data
    assert "trigger_device_id" in data


# ============================================================================
# POST /api/events/{id}/ack/ — acknowledge
# ============================================================================


def test_ack_event_returns_200(client, client_token, event):
    response = client.post(f"/api/events/{event.id}/ack/", **auth(client_token))
    assert response.status_code == 200


def test_ack_event_sets_acknowledged_true(client, client_token, event):
    assert event.acknowledged is False

    client.post(f"/api/events/{event.id}/ack/", **auth(client_token))

    event.refresh_from_db()
    assert event.acknowledged is True


def test_ack_event_response_contains_acknowledged_true(client, client_token, event):
    response = client.post(f"/api/events/{event.id}/ack/", **auth(client_token))
    data = response.json()
    assert data["acknowledged"] is True


def test_ack_event_returns_404_for_unknown_id(client, client_token):
    response = client.post("/api/events/99999/ack/", **auth(client_token))
    assert response.status_code == 404
    assert "detail" in response.json()


def test_ack_event_returns_401_without_token(client, event):
    response = client.post(f"/api/events/{event.id}/ack/")
    assert response.status_code == 401


def test_ack_event_is_idempotent(client, client_token, event):
    """Calling ack twice should keep acknowledged=True and not error"""
    client.post(f"/api/events/{event.id}/ack/", **auth(client_token))
    response = client.post(f"/api/events/{event.id}/ack/", **auth(client_token))

    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True

    event.refresh_from_db()
    assert event.acknowledged is True


def test_ack_event_already_acknowledged_remains_200(client, client_token, event_acked):
    response = client.post(f"/api/events/{event_acked.id}/ack/", **auth(client_token))
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True


def test_ack_event_by_admin_returns_200(client, admin_token, event):
    response = client.post(f"/api/events/{event.id}/ack/", **auth(admin_token))
    assert response.status_code == 200


def test_ack_event_response_contains_rule_info(client, client_token, event, rule):
    response = client.post(f"/api/events/{event.id}/ack/", **auth(client_token))
    data = response.json()
    assert data["rule"]["id"] == rule.id
    assert data["rule"]["name"] == rule.name


def test_ack_event_does_not_change_other_events(client, client_token, rule):
    e1 = Event.objects.create(rule=rule)
    e2 = Event.objects.create(rule=rule)

    client.post(f"/api/events/{e1.id}/ack/", **auth(client_token))

    e2.refresh_from_db()
    assert e2.acknowledged is False


