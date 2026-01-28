# Pytest Setup & Configuration Guide

## Overview

This document explains the pytest infrastructure set up to enable testing of Django management commands and applications in the IoT-Hub project. The setup ensures that pytest can properly access Django settings and the test database.

## Files Created

### 1. `/backend/conftest.py`

**Purpose**: Pytest configuration hook to set up Django before running tests.

**Location**: `/backend/conftest.py`

**Content**:
```python
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

```

**Why it's needed**:
- `pytest_configure()` runs before any tests are collected
- Ensures Django is properly initialized with settings
- Allows pytest to access database connections and Django ORM


## Pytest Markers & Decorators

### `@pytest.mark.django_db`

**Purpose**: Allows a test to access the Django ORM and database.

**Usage**:
```python
@pytest.mark.django_db
class TestSetupTimescaleDB:
    def test_something(self):
        # Can use Django models and database here
        pass
```

**Why it's needed**: By default, pytest-django prevents database access to avoid unintended side effects. This marker explicitly grants access.

## Docker Execution

### Running Tests Inside Docker

All tests must be run inside the Docker container where Django and all dependencies are available.

**Command format**:
```bash
docker compose exec web pytest <path/to/test_file> <options>
```

