import json
import pytest
from unittest.mock import Mock, patch, create_autospec

from django.test import override_settings

from producers.kafka_producer import KafkaProducer, ProduceResult


def post_json(client, url, payload, sync: bool = True, headers=None):
    headers = headers or {}
    if sync:
        headers['HTTP_INGEST_SYNC'] = '1'

    return client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json',
        **headers,
    )


@pytest.mark.django_db
@patch('apps.devices.views.telemetry_views.get_telemetry_raw_producer')
def test_request_triggers_telemetry_producer(
    get_producer_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test view triggers 202 and activates KafkaProducer produce()."""
    producer = create_autospec(KafkaProducer, instance=True)
    producer.produce.return_value = ProduceResult.ENQUEUED
    get_producer_mock.return_value = producer

    res = post_json(
        client,
        telemetry_ingest_url,
        valid_telemetry_payload,
        sync=False,
    )

    assert res.status_code == 202
    producer.produce.assert_called_once()

    data = res.json()
    assert data['status'] == 'accepted'


# ------------ tests for dev-only sync mode ------------


@pytest.mark.django_db
@override_settings(DEBUG=True)
@patch('apps.devices.views.telemetry_views.telemetry_create')
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


@pytest.mark.django_db
@override_settings(DEBUG=True)
@patch('apps.devices.views.telemetry_views.telemetry_create')
def test_ingest_single_service_rejects_returns_400(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
):
    """Test service reject returns 422."""
    telemetry_create_mock.return_value = Mock(created_count=0, errors={'device': 'invalid'})

    res = post_json(client, telemetry_ingest_url, valid_telemetry_payload)

    assert res.status_code == 422
    telemetry_create_mock.assert_called_once()

    data = res.json()
    assert data['status'] == 'rejected'
    assert data['created'] == 0
    assert 'errors' in data


@pytest.mark.django_db
@override_settings(DEBUG=True)
@patch('apps.devices.views.telemetry_views.telemetry_create')
def test_ingest_batch_valid_returns_201(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
    active_device,
    device_metric_numeric,
    device_metric_bool,
    device_metric_str,
):
    telemetry_create_mock.return_value = Mock(created_count=2, errors={})

    batch = [valid_telemetry_payload, valid_telemetry_payload]
    res = post_json(client, telemetry_ingest_url, batch)

    assert res.status_code == 201
    telemetry_create_mock.assert_called_once()

    data = res.json()
    assert data['status'] == 'ok'
    assert data['created'] == 2


@pytest.mark.django_db
@override_settings(DEBUG=True)
@patch('apps.devices.views.telemetry_views.telemetry_create')
def test_ingest_batch_mixed_valid_invalid(
    telemetry_create_mock,
    client,
    telemetry_ingest_url,
    valid_telemetry_payload,
    active_device,
    device_metric_numeric,
    device_metric_bool,
    device_metric_str,
):
    """Test mixed batch ingests valid items, reports errors for invalid ones."""
    telemetry_create_mock.return_value = Mock(
        created_count=2, errors={'1': {'device': 'device must be of type str.'}}
    )

    invalid_item = dict(valid_telemetry_payload)
    invalid_item['device'] = 123

    batch = [valid_telemetry_payload, invalid_item, valid_telemetry_payload]
    res = post_json(client, telemetry_ingest_url, batch)

    assert res.status_code == 201
    telemetry_create_mock.assert_called_once()

    data = res.json()
    assert data['created'] == 2

    assert '1' in data['errors']
    assert 'device' in data['errors']['1']


@pytest.mark.django_db
@override_settings(DEBUG=True)
@patch('apps.devices.views.telemetry_views.telemetry_create')
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


@override_settings(DEBUG=True)
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


@override_settings(DEBUG=True)
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
