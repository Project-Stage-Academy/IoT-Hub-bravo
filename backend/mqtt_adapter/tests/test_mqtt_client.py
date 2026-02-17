from unittest.mock import Mock, create_autospec

import pytest

from mqtt_adapter.config import MqttConfig
from mqtt_adapter.message_handlers import MQTTJsonMessage, MessageHandler
from mqtt_adapter.mqtt_client import MqttCallbacks


@pytest.fixture
def config():
    return MqttConfig(
        host='localhost',
        port=1883,
        keepalive=60,
        topic='telemetry',
        qos=1,
        client_id='test-client',
    )


@pytest.fixture
def handler():
    return create_autospec(MessageHandler, instance=True)


def mqtt_message(payload: bytes, topic='telemetry', qos=1, retain=0):
    """Minimal MQTTMessage mock object."""
    m = Mock()
    m.payload = payload
    m.topic = topic
    m.qos = qos
    m.retain = retain
    return m


@pytest.mark.parametrize(
    'payload,expected_type',
    [
        (b'{"a": 1}', dict),
        (b'[1, 2, 3]', list),
        (b'{"nested": {"x": 1}}', dict),
    ],
)
def test_payload_to_json_accepts_dict_and_list(payload, expected_type):
    """Test _payload_to_json accepts valid JSON dict/list payloads."""
    obj = MqttCallbacks._payload_to_json(payload)
    assert isinstance(obj, expected_type)


@pytest.mark.parametrize(
    'payload',
    [
        b'"string"',
        b'123',
        b'true',
        b'null',
        b'{"a": 1',
        b'\xff\xfe\xfd',
    ],
)
def test_payload_to_json_rejects_non_object_and_invalid(payload):
    """
    Test _payload_to_json rejects invalid JSON/UTF-8
    and non dict/list JSON values.
    """
    assert MqttCallbacks._payload_to_json(payload) is None


def test_on_connect_subscribes_on_success(config, handler):
    """Test on_connect subscribes when rc == 0."""
    callbacks = MqttCallbacks(config=config, handler=handler)

    client = Mock()
    callbacks.on_connect(client, userdata=None, flags={}, rc=0)

    client.subscribe.assert_called_once_with(config.topic, qos=config.qos)


def test_on_connect_does_not_subscribe_on_error(config, handler):
    """Test on_connect does not subscribe when rc != 0."""
    callbacks = MqttCallbacks(config=config, handler=handler)
    client = Mock()

    callbacks.on_connect(client, userdata=None, flags={}, rc=5)

    client.subscribe.assert_not_called()


def test_on_message_calls_handler_on_valid_json(config, handler):
    """Test on_message calls handle_payload for valid JSON dict/list."""
    callbacks = MqttCallbacks(config=config, handler=handler)
    client = Mock()

    message = mqtt_message(b'{"device": "DEV-001"}')
    callbacks.on_message(client, userdata=None, m=message)

    handler.handle.assert_called_once()
    args = handler.handle.call_args.args
    assert isinstance(args[0], MQTTJsonMessage)
    assert args[0].payload['device'] == 'DEV-001'


def test_on_message_does_not_call_handler_on_invalid_json(config, handler):
    """
    Test on_message rejects invalid payload
    and does not call handle_payload.
    """
    callbacks = MqttCallbacks(config=config, handler=handler)
    client = Mock()

    message = mqtt_message(b'{"invalid": "json"')
    callbacks.on_message(client, userdata=None, m=message)

    handler.handle.assert_not_called()


def test_on_message_does_not_crash_if_handler_raises(config, handler):
    """Test on_message catches handler exceptions."""
    handler.handle.side_effect = ValueError('invalid-value')
    callbacks = MqttCallbacks(config=config, handler=handler)

    client = Mock()
    message = mqtt_message(b'{"x": 1}')

    # will fail if exception raises
    callbacks.on_message(client, userdata=None, m=message)

    handler.handle.assert_called_once()
