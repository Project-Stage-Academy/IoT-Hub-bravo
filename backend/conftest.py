"""
Pytest configuration for Django tests.
Sets up Django settings before running tests.
"""

import os
import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings before tests run."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

    if not settings.configured:
        django.setup()
