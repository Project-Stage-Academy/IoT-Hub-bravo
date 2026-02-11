"""
Pytest configuration and shared fixtures for the IoT Hub test suite.
"""

import os
import django
import pytest
from django.conf import settings
from django.test import Client


def pytest_configure():
    """Configure Django settings before tests run."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
    if not settings.configured:
        django.setup()


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """HTTP test client for API endpoint testing."""
    return Client()


@pytest.fixture
def authenticated_client(client, db):
    """Django test client logged in as regular user."""
    from tests.fixtures.factories import UserFactory
    user = UserFactory()
    client.login(username=user.username, password="testpass123")
    return client


@pytest.fixture
def admin_client(client, db):
    """Django test client logged in as superuser."""
    from tests.fixtures.factories import AdminUserFactory
    user = AdminUserFactory()
    client.login(username=user.username, password="testpass123")
    return client
