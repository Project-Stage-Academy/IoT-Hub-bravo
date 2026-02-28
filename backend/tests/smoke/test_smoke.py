"""
Smoke tests for critical flows.
Run before demos: docker compose exec web pytest tests/smoke/ -v
"""

import json
import jwt
from datetime import datetime, timedelta, timezone

import pytest
from django.conf import settings

from tests.fixtures.factories import UserFactory

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

    def test_device_api_crud_smoke(self, client):
        """
        Smoke test: Device API CRUD operations work.
        """
        user = UserFactory(role="admin")
        token = jwt.encode(
            {
                "sub": user.id,
                "role": "admin",
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                ),
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
