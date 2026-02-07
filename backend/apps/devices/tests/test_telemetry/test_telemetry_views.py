import json
from unittest.mock import Mock, patch

from django.test import override_settings


def post_json(client, url, payload, headers=None):
    headers = headers or {}
    return client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json',
        **headers,
    )


@patch('apps.devices.views.telemetry_create')
def test_ingest_single_valid_returns_201(
    telemetry_create_mock, client, telemetry_ingest_url, valid_telemetry_payload
):
    """Test single valid payload returns 201 and calls service once."""
    telemetry_create_mock.return_value = Mock(created_count=2, errors={})

    res = post_json(client, telemetry_ingest_url, valid_telemetry_payload)

    assert res.status_code == 201
    telemetry_create_mock.assert_called_once()

    data = res.json()
    assert data['status'] == 'ok'
    assert data['created'] == 2
    assert 'errors' in data


@patch('apps.devices.views.telemetry_create')
def test_ingest_single_service_rejects_returns_400(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test service reject returns 400."""
    telemetry_create_mock.return_value = Mock(created_count=0, errors={'device': 'invalid'})

    res = post_json(
        client,
        telemetry_ingest_url,
        valid_telemetry_payload,
    )

    assert res.status_code == 400
    telemetry_create_mock.assert_called_once()

    data = res.json()
    assert data['status'] == 'rejected'
    assert data['created'] == 0
    assert 'errors' in data


@patch('apps.devices.views.telemetry_create')
def test_ingest_batch_valid_returns_201(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test batch valid payload returns 201 and calls service for each valid item."""
    telemetry_create_mock.return_value = Mock(created_count=1, errors={})

    res = post_json(
        client, telemetry_ingest_url, [valid_telemetry_payload, valid_telemetry_payload]
    )

    assert res.status_code == 201
    assert telemetry_create_mock.call_count == 2

    data = res.json()
    assert data['status'] == 'ok'
    assert data['created'] == 2
    assert 'items' in data
    assert isinstance(data['items'], list)
    assert len(data['items']) == 2


@patch('apps.devices.views.telemetry_create')
def test_ingest_batch_mixed_valid_invalid(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test mixed batch ingests valid items, reports errors for invalid ones."""
    telemetry_create_mock.return_value = Mock(created_count=1, errors={})

    invalid_item = dict(valid_telemetry_payload)
    invalid_item['device'] = 123

    batch = [valid_telemetry_payload, invalid_item, valid_telemetry_payload]

    res = post_json(client, telemetry_ingest_url, batch)

    assert res.status_code == 201
    assert telemetry_create_mock.call_count == 2

    data = res.json()
    assert data['created'] == 2
    assert 'errors' in data
    assert '1' in {str(k) for k in data['errors'].keys()} or 1 in data['errors']


@patch('apps.devices.views.telemetry_create')
def test_ingest_batch_all_invalid_returns_400(
    telemetry_create_mock, client, telemetry_ingest_url, valid_telemetry_payload
):
    """Test batch with no valid items returns 400 and does not call service."""
    invalid_item1 = dict(valid_telemetry_payload)
    invalid_item1['device'] = 123

    invalid_item2 = dict(valid_telemetry_payload)
    invalid_item2['metrics'] = 'invalid'

    res = post_json(client, telemetry_ingest_url, [invalid_item1, invalid_item2])

    assert res.status_code == 400
    telemetry_create_mock.assert_not_called()

    data = res.json()
    assert 'errors' in data


def test_ingest_malformed_json_returns_400(client, telemetry_ingest_url):
    """Test malformed JSON returns 400."""
    res = client.post(
        telemetry_ingest_url,
        data='{bad-json',
        content_type='application/json',
    )

    assert res.status_code == 400

    data = res.json()
    assert 'errors' in data
    assert 'json' in data['errors']


def test_ingest_wrong_payload_type_returns_400(client, telemetry_ingest_url):
    """Test payload that is not object/array returns 400."""
    res = client.post(
        telemetry_ingest_url,
        data=json.dumps(123),
        content_type='application/json',
    )

    assert res.status_code == 400

    data = res.json()
    assert 'errors' in data
    assert 'json' in data['errors']


@override_settings(TELEMETRY_ASYNC_HEADER='Ingest-Async')
@patch('apps.devices.views.ingest_telemetry_payload')
def test_ingest_async_header_triggers_celery_delay(
    ingest_task_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test Ingest-Async header triggers 202 and schedules celery task."""
    res = post_json(
        client,
        telemetry_ingest_url,
        valid_telemetry_payload,
        headers={'HTTP_INGEST_ASYNC': '1'},
    )

    assert res.status_code == 202
    ingest_task_mock.delay.assert_called_once()

    data = res.json()
    assert data['status'] == 'accepted'


@override_settings(TELEMETRY_ASYNC_HEADER='Ingest-Async')
@override_settings(TELEMETRY_ASYNC_BATCH_THRESHOLD=5)
@patch('apps.devices.views.ingest_telemetry_payload')
def test_ingest_async_large_batch_triggers_celery_delay(
    ingest_task_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test large batch triggers async ingestion and returns 202."""
    batch = [valid_telemetry_payload] * 6

    res = post_json(client, telemetry_ingest_url, batch)

    assert res.status_code == 202
    ingest_task_mock.delay.assert_called_once()

    data = res.json()
    assert data['status'] == 'accepted'
