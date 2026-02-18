# Testing Guide
 
This document describes the testing infrastructure, conventions, and best practices for the IoT Hub backend.
 
## Quick Start
 
Run all tests inside Docker:
 
```bash
docker compose exec web pytest
```
 
Run with verbose output:
 
```bash
docker compose exec web pytest -v
```
 
Run specific test file:
 
```bash
docker compose exec web pytest tests/models/test_device.py -v
```
 
Run specific test:
 
```bash
docker compose exec web pytest tests/models/test_device.py::TestDeviceCreation::test_create_device -v
```
 
## Test Structure
 
```
backend/
├── tests/
│   ├── models/          # Unit tests for Django models
│   ├── api/             # API endpoint tests (Sub-Issue B)
│   ├── integration/     # Integration tests (Sub-Issue B)
│   ├── smoke/           # Smoke tests
│   ├── fixtures/        # Shared test utilities
│   │   └── factories.py # Factory Boy factories
│   └── utils/           # Test helpers
├── conftest.py          # Pytest fixtures
└── pyproject.toml       # Pytest & coverage configuration
```
 
## Factories
 
We use [Factory Boy](https://factoryboy.readthedocs.io/) to create test data. Factories are defined in `tests/fixtures/factories.py`.
 
### Available Factories
 
| Factory | Model | Notes |
|---------|-------|-------|
| `UserFactory` | User | Creates user with unique email |
| `DeviceFactory` | Device | Active device by default |
| `MetricFactory` | Metric | Numeric type by default |
| `DeviceMetricFactory` | DeviceMetric | Links device and metric |
| `TelemetryFactory` | Telemetry | Numeric value by default |
| `TelemetryBooleanFactory` | Telemetry | Boolean value |
| `TelemetryStringFactory` | Telemetry | String value |
| `RuleFactory` | Rule | Active rule by default |
| `EventFactory` | Event | Not acknowledged by default |
 
### Usage Examples
 
```python
from tests.fixtures.factories import DeviceFactory, TelemetryFactory
 
# Create a device
device = DeviceFactory()
 
# Create a device with custom name
device = DeviceFactory(name="Custom Device")
 
# Create inactive device
device = DeviceFactory(is_active=False)
 
# Create telemetry with specific value
telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "42.5"})
```
 
## Fixtures
 
Reusable fixtures are defined in `conftest.py`. Use them in tests:
 
```python
def test_something(device, metric):
    # device and metric are created automatically
    assert device.is_active is True
```
 
### Available Fixtures
 
- `regular_user`, `staff_user`, `superuser` — User instances
- `device`, `inactive_device` — Device instances
- `metric`, `metric_boolean`, `metric_string` — Metric instances
- `device_metric` — DeviceMetric instance
- `telemetry`, `telemetry_batch` — Telemetry instances
- `rule`, `inactive_rule` — Rule instances
- `event`, `acknowledged_event` — Event instances
 
## Coverage
 
Coverage is configured in `pyproject.toml` and runs automatically with pytest.
 
### View Coverage Report
 
After running tests:
 
```bash
# Terminal report
docker compose exec web coverage report
 
# HTML report (open backend/htmlcov/index.html in browser)
docker compose exec web coverage html
```
 
### Coverage Threshold
 
Current minimum coverage: **35%** (will increase as more tests are added)
 
Coverage fails CI if below threshold:
 
```
FAIL Required test coverage of 35% not reached. Total coverage: 30.00%
```
 
## Writing Tests
 
### Test Class Naming
 
```python
class TestDeviceCreation:
    """Tests for Device model creation."""
 
class TestDeviceConstraints:
    """Tests for Device model constraints."""
 
class TestDeviceStringRepresentation:
    """Tests for Device __str__ method."""
```
 
### Test Method Naming
 
```python
def test_create_device_with_required_fields(self):
    """Test creating a device with all required fields."""
 
def test_device_name_max_length_constraint(self):
    """Test that device name cannot exceed 255 characters."""
```
 
### Database Access
 
All tests that need database access must be marked:
 
```python
import pytest
 
pytestmark = pytest.mark.django_db
 
class TestDevice:
    def test_something(self):
        ...
```
 
### Testing Constraints
 
```python
from django.db import IntegrityError
 
def test_unique_constraint(self):
    DeviceFactory(serial_number="ABC123")
 
    with pytest.raises(IntegrityError):
        DeviceFactory(serial_number="ABC123")
```
 
### Testing Generated Fields
 
For models with `GeneratedField`, refresh from DB after creation:
 
```python
def test_generated_field(self):
    telemetry = TelemetryFactory(value_jsonb={"t": "numeric", "v": "25.5"})
    telemetry.refresh_from_db()
 
    assert telemetry.value_numeric == Decimal("25.5")
```
 
## Common Issues
 
### "Now() != Now()" Error
 
Models with `default=models.functions.Now()` store SQL function, not Python datetime.
 
**Wrong:**
```python
def test_timestamp(self):
    event = EventFactory()
    assert event.timestamp >= timezone.now()  # TypeError!
```
 
**Correct:**
```python
def test_timestamp(self):
    event = EventFactory()
    event.refresh_from_db()
    assert event.timestamp is not None
```
 
Or pass explicit timestamp:
```python
def test_timestamp(self):
    now = timezone.now()
    event = EventFactory(timestamp=now)
    assert event.timestamp == now
```
 
### Database Connection Error
 
If you see "failed to resolve host 'db'", you're running pytest outside Docker:
 
```bash
# Wrong (from local machine)
pytest tests/
 
# Correct (inside Docker)
docker compose exec web pytest tests/
```
 
## See Also
 
- [CI Pipeline](ci.md) — CI configuration and test flakiness
- [Development Environment](dev-environment.md) — Local setup
 