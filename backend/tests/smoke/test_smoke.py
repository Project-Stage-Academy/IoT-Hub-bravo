"""
Smoke tests for critical flows.
Run before demos: docker compose exec web pytest tests/smoke/ -v
"""

import json
import jwt
from datetime import datetime, timedelta, timezone

import pytest
from celery import current_app
from django.conf import settings

from apps.devices.models import Device, Telemetry
from apps.rules.models import Event
from apps.rules.services.rule_processor import run_rule_processor_task
from tests.fixtures.factories import (
    DeviceFactory,
    DeviceMetricFactory,
    MetricFactory,
    RuleFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_ci_smoke():
    """
    Placeholder test to ensure that CI runs
    pytest and collects at least one test.
    """
    assert True


class TestCriticalFlowsSmoke:
    """
    Smoke tests for critical flows.
    Run these before demos to verify core functionality works.
    """

    @pytest.fixture(autouse=True)
    def celery_eager_mode(self, settings):
        """Run Celery tasks synchronously."""
        settings.CELERY_TASK_ALWAYS_EAGER = True
        current_app.conf.task_always_eager = True

    def test_full_flow_device_telemetry_rule_event(self, client):
        """
        Critical flow: Device registration → Telemetry ingestion → Rule firing → Event created.

        This is the core IoT Hub flow that must always work.
        """
        # Step 1: Device registration (via factory, simulating API)
        user = UserFactory(role="admin")
        device = DeviceFactory(
            serial_id="SMOKE-001",
            name="Smoke Test Device",
            user=user,
            is_active=True,
        )
        assert Device.objects.filter(serial_id="SMOKE-001").exists()

        # Step 2: Setup metric and link to device
        metric = MetricFactory(metric_type="temperature", data_type="numeric")
        device_metric = DeviceMetricFactory(device=device, metric=metric)

        # Step 3: Create rule (threshold: temperature > 30)
        rule = RuleFactory(
            name="High Temperature Alert",
            device_metric=device_metric,
            condition={"type": "threshold", "operator": ">", "value": 30},
            is_active=True,
        )

        # Step 4: Telemetry ingestion via API
        payload = {
            "device": "SMOKE-001",
            "metrics": {"temperature": "35"},  # 35 > 30, should trigger rule
            "ts": "2024-01-15T10:30:00Z",
        }

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        assert response.json()["created"] == 1

        # Step 5: Get the created telemetry and run rule processor
        telemetry = Telemetry.objects.filter(device_metric=device_metric).first()
        assert telemetry is not None

        run_rule_processor_task(telemetry.id)

        # Step 6: Assert Event was created
        events = Event.objects.filter(rule=rule)
        assert events.count() == 1, "Event should be created when rule fires"
        assert events.first().trigger_telemetry_id == telemetry.id

    def test_device_api_crud_smoke(self, client):
        """
        Smoke test: Device API CRUD operations work.
        """
        user = UserFactory(role="admin")
        token = jwt.encode(
            {
                "sub": user.id,
                "role": "admin",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        # CREATE
        response = client.post(
            "/api/devices/",
            data=json.dumps(
                {
                    "schema_version": "v1",
                    "device": {
                        "name": "Smoke CRUD Device",
                        "serial_id": "SMOKE-CRUD-001",
                        "user_id": user.id,
                    },
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 201, "Device creation should work"

        device_id = response.json()["id"]

        # READ
        response = client.get(
            f"/api/devices/{device_id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200, "Device read should work"

        # DELETE
        response = client.delete(
            f"/api/devices/{device_id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 204, "Device delete should work"

    def test_telemetry_ingestion_smoke(self, client):
        """
        Smoke test: Telemetry ingestion endpoint works.
        """
        device = DeviceFactory(serial_id="SMOKE-TEL-001")
        metric = MetricFactory(metric_type="humidity", data_type="numeric")
        DeviceMetricFactory(device=device, metric=metric)

        response = client.post(
            "/api/telemetry/",
            data=json.dumps(
                {
                    "device": "SMOKE-TEL-001",
                    "metrics": {"humidity": "65.5"},
                    "ts": "2024-01-15T12:00:00Z",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201, "Telemetry ingestion should work"
        assert response.json()["status"] == "ok"
