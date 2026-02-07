from unittest.mock import patch

from apps.devices.tasks import ingest_telemetry_payload


@patch('apps.devices.tasks.telemetry_create')
def test_task_rejects_invalid_payload_type(telemetry_create_mock):
    """Test task rejects non-dict/non-list payload and does not call service."""
    ingest_telemetry_payload(payload='invalid-payload')
    telemetry_create_mock.assert_not_called()


@patch('apps.devices.tasks.telemetry_create')
def test_dict_payload_calls_service_once(
    telemetry_create_mock,
    valid_telemetry_payload,
):
    """Test dict payload is treated as a batch of one and calls service once."""
    ingest_telemetry_payload(payload=valid_telemetry_payload)
    telemetry_create_mock.assert_called_once()

    kwargs = telemetry_create_mock.call_args.kwargs
    assert set(kwargs.keys()) == {'device_serial_id', 'metrics', 'ts'}
    assert kwargs['device_serial_id'] == 'DEV-001'


@patch('apps.devices.tasks.telemetry_create')
def test_batch_payload_calls_service_for_every_item(
    telemetry_create_mock,
    valid_telemetry_payload,
):
    """Test dict payload is treated as a batch of one and calls service once."""
    ingest_telemetry_payload(payload=[valid_telemetry_payload] * 3)
    assert telemetry_create_mock.call_count == 3


@patch('apps.devices.tasks.telemetry_create')
def test_invalid_batch_does_not_call_service(
    telemetry_create_mock,
    valid_telemetry_payload,
):
    """Test invalid batch payload does not call service."""
    invalid_item1 = dict(valid_telemetry_payload)
    invalid_item1['schema_version'] = 'invalid-schema'

    invalid_item2 = dict(valid_telemetry_payload)
    invalid_item2['metrics'] = 999

    ingest_telemetry_payload(payload=[invalid_item1, invalid_item2])
    telemetry_create_mock.assert_not_called()


@patch('apps.devices.tasks.telemetry_create')
def test_service_called_for_valid_items_only(
    telemetry_create_mock,
    valid_telemetry_payload,
):
    """Test task calls service only for valid items in a batch."""
    valid_item1 = dict(valid_telemetry_payload)
    valid_item2 = dict(valid_telemetry_payload)

    invalid_item = dict(valid_telemetry_payload)
    invalid_item['device'] = 123

    ingest_telemetry_payload(payload=[valid_item1, invalid_item, valid_item2])
    assert telemetry_create_mock.call_count == 2
