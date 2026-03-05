"""Pytest configuration for Django tests."""

import os
import sys

# Ensure project root is in sys.path before django.setup()
_rootdir = os.path.dirname(os.path.abspath(__file__))
if _rootdir not in sys.path:
    sys.path.insert(0, _rootdir)

import django # noqa: E402
import pytest # noqa: E402
from django.conf import settings # noqa: E402
from django.test import Client # noqa: E402


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
