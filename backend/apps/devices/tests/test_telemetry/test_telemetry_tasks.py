from typing import Optional
from unittest.mock import patch, MagicMock

from apps.devices.tasks import ingest_telemetry_payload


def validation_result(validated_rows: Optional[list] = None, errors: Optional[list] = None):
    return MagicMock(
        validated_rows=validated_rows or [],
        errors=errors or [],
    )


@patch('apps.devices.tasks.telemetry_validate')
@patch('apps.devices.tasks.telemetry_create')
def test_task_rejects_invalid_payload_type(telemetry_create_mock, telemetry_validate_mock):
    """Test task rejects non-dict/non-list payload and does not call service."""
    ingest_telemetry_payload(payload='invalid-payload')

    telemetry_validate_mock.assert_not_called()
    telemetry_create_mock.assert_not_called()


@patch('apps.devices.tasks.telemetry_validate')
@patch('apps.devices.tasks.telemetry_create')
def test_dict_payload_processed_as_batch_of_one(
    telemetry_create_mock,
    telemetry_validate_mock,
    valid_telemetry_payload,
    validated_telemetry_row,
):
    """Test dict payload is treated as a batch of one and calls create service."""
    telemetry_validate_mock.return_value = validation_result([validated_telemetry_row])
    telemetry_create_mock.return_value.created_count = 1
    telemetry_create_mock.return_value.attempted_count = 1
    telemetry_create_mock.return_value.errors = []

    ingest_telemetry_payload(payload=valid_telemetry_payload)

    telemetry_validate_mock.assert_called_once()
    telemetry_create_mock.assert_called_once()

    kwargs = telemetry_create_mock.call_args.kwargs
    assert 'valid_data' in kwargs
    assert isinstance(kwargs['valid_data'], list)
    assert len(kwargs['valid_data']) == 1


@patch('apps.devices.tasks.telemetry_validate')
@patch('apps.devices.tasks.telemetry_create')
def test_batch_payload_calls_create_service_with_every_item(
    telemetry_create_mock,
    telemetry_validate_mock,
    valid_telemetry_payload,
    validated_telemetry_row,
):
    """Test all validated items are passed to create service."""
    telemetry_validate_mock.return_value = validation_result([validated_telemetry_row] * 3)
    telemetry_create_mock.return_value.created_count = 3
    telemetry_create_mock.return_value.attempted_count = 3
    telemetry_create_mock.return_value.errors = []

    ingest_telemetry_payload(payload=[valid_telemetry_payload] * 3)

    telemetry_validate_mock.assert_called_once()
    telemetry_create_mock.assert_called_once()

    valid_data = telemetry_create_mock.call_args.kwargs['valid_data']
    assert len(valid_data) == 3


@patch('apps.devices.tasks.telemetry_validate')
@patch('apps.devices.tasks.telemetry_create')
def test_create_service_called_for_valid_items_only(
    telemetry_create_mock,
    telemetry_validate_mock,
    valid_telemetry_payload,
    validated_telemetry_row,
):
    """
    Test validated items are passed to create service
    without failing on validation errors.
    """
    telemetry_validate_mock.return_value = validation_result(
        validated_rows=[validated_telemetry_row] * 2,
        errors=[{'item3': 'error3'}],
    )
    telemetry_create_mock.return_value.created_count = 2
    telemetry_create_mock.return_value.attempted_count = 2
    telemetry_create_mock.return_value.errors = []

    ingest_telemetry_payload(payload=[valid_telemetry_payload] * 3)

    telemetry_validate_mock.assert_called_once()
    telemetry_create_mock.assert_called_once()

    payload = telemetry_create_mock.call_args.kwargs['valid_data']
    assert len(payload) == 2
