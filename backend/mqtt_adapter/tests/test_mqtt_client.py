from unittest.mock import Mock, create_autospec, patch
 
import pytest

import logging
 
from mqtt_adapter.config import MqttConfig
from mqtt_adapter.message_handlers import MQTTJsonMessage, MessageHandler
from mqtt_adapter.mqtt_client import (
    MqttCallbacks,
    _normalize_credential,
    apply_mqtt_auth,
    build_client,
    get_mqtt_client,
)


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


# ──────────────────────────────────────────────
#  _normalize_credential
# ──────────────────────────────────────────────


class TestNormalizeCredential:
    """Tests for _normalize_credential helper."""

    def test_strips_whitespace(self):

        assert _normalize_credential('  admin  ') == 'admin'

    def test_empty_string_returns_none(self):

        assert _normalize_credential('   ') is None

    def test_valid_string_returns_stripped(self):

        assert _normalize_credential('my-user') == 'my-user'


# ──────────────────────────────────────────────
#  apply_mqtt_auth
# ──────────────────────────────────────────────


class TestApplyMqttAuth:
    """Tests for apply_mqtt_auth function."""

    def test_sets_credentials(self, config):

        client = Mock()
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test',
            username='admin',
            password='secret',
        )

        apply_mqtt_auth(client, cfg)

        client.username_pw_set.assert_called_once_with('admin', 'secret')

    def test_raises_on_empty_username(self, config):

        client = Mock()
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test',
            username='   ',
            password='secret',
        )

        with pytest.raises(ValueError, match='MQTT_USERNAME'):
            apply_mqtt_auth(client, cfg)

    def test_raises_on_empty_password(self, config):

        client = Mock()
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test',
            username='admin',
            password='   ',
        )

        with pytest.raises(ValueError, match='MQTT_PASSWORD'):
            apply_mqtt_auth(client, cfg)


# ──────────────────────────────────────────────
#  build_client
# ──────────────────────────────────────────────


class TestBuildClient:
    """Tests for build_client function."""

    @patch('mqtt_adapter.mqtt_client.mqtt.Client')
    def test_sets_callbacks(self, mock_client_cls, config, handler):

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test-client',
            username='admin',
            password='secret',
        )
        callbacks = MqttCallbacks(config=cfg, handler=handler)
        client = build_client(cfg, callbacks)

        assert client.on_connect == callbacks.on_connect
        assert client.on_disconnect == callbacks.on_disconnect
        assert client.on_message == callbacks.on_message

    @patch('mqtt_adapter.mqtt_client.mqtt.Client')
    def test_sets_reconnect_delay(self, mock_client_cls, config, handler):

        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test-client',
            username='admin',
            password='secret',
            min_reconnect_delay=5,
            max_reconnect_delay=300,
        )
        callbacks = MqttCallbacks(config=cfg, handler=handler)
        build_client(cfg, callbacks)

        mock_client.reconnect_delay_set.assert_called_once_with(
            min_delay=5,
            max_delay=300,
        )


# ──────────────────────────────────────────────
#  on_disconnect
# ──────────────────────────────────────────────


class TestOnDisconnect:
    """Tests for MqttCallbacks.on_disconnect."""

    def test_unexpected_disconnect_logs_warning(self, config, handler, caplog):

        callbacks = MqttCallbacks(config=config, handler=handler)

        with caplog.at_level(logging.WARNING, logger='mqtt_adapter.mqtt_client'):
            callbacks.on_disconnect(Mock(), userdata=None, rc=1)

        assert 'Unexpected MQTT disconnect' in caplog.text


# ──────────────────────────────────────────────
#  get_mqtt_client
# ──────────────────────────────────────────────


class TestGetMqttClient:
    """Tests for get_mqtt_client function."""

    @patch('mqtt_adapter.mqtt_client.build_client')
    def test_calls_connect_async(self, mock_build_client, handler):

        mock_client = Mock()
        mock_build_client.return_value = mock_client

        cfg = MqttConfig(
            host='broker.local',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test-client',
            username='admin',
            password='secret',
        )
        result = get_mqtt_client(config=cfg, handler=handler)

        mock_client.connect_async.assert_called_once_with(
            'broker.local',
            1883,
            keepalive=60,
        )
        assert result is mock_client
