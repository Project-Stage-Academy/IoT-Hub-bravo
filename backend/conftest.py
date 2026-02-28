"""Pytest configuration for Django tests."""

import os
import django
import pytest
from django.conf import settings
from django.test import Client


def pytest_configure():
    """Configure Django settings before tests run."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
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
