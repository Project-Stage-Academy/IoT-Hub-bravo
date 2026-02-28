"""API tests for Auth endpoints."""

import json

import pytest

from tests.fixtures.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestLoginAPI:
    """Tests for POST /api/auth/login/"""

    def test_login_success(self, client):
        """Test successful login returns token."""
        user = UserFactory(username="testuser")
        user.set_password("testpass123")
        user.save()

        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self, client):
        """Test login with wrong password returns 401."""
        user = UserFactory()
        user.set_password("testpass123")
        user.save()

        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"username": user.email, "password": "wrongpassword"}),
            content_type="application/json",
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["error"]

    def test_login_user_not_found(self, client):
        """Test login with non-existent user returns 401."""
        response = client.post(
            "/api/auth/login/",
            data=json.dumps(
                {"username": "nonexistent@test.com", "password": "testpass"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_login_missing_username(self, client):
        """Test login without username returns 400."""
        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"password": "testpass123"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "Username" in response.json()["error"]

    def test_login_missing_password(self, client):
        """Test login without password returns 400."""
        response = client.post(
            "/api/auth/login/",
            data=json.dumps({"username": "test@test.com"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "Password" in response.json()["error"]

    def test_login_invalid_json(self, client):
        """Test login with invalid JSON returns 400."""
        response = client.post(
            "/api/auth/login/",
            data="not valid json",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]

    def test_login_method_not_allowed(self, client):
        """Test that GET method is not allowed."""
        response = client.get("/api/auth/login/")

        assert response.status_code == 405
