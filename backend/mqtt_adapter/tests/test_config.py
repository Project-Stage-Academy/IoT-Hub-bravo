import pytest
from dataclasses import FrozenInstanceError

from mqtt_adapter.config import MqttConfig


class TestMqttConfig:
    """Unit tests for MqttConfig dataclass."""

    def test_explicit_values_stored(self):
        """Test that explicitly passed values are stored correctly."""
        cfg = MqttConfig(
            host='broker.example.com',
            port=8883,
            keepalive=120,
            topic='sensors/+/data',
            qos=2,
            client_id='my-client',
            username='admin',
            password='secret',
            min_reconnect_delay=5,
            max_reconnect_delay=300,
        )
        assert cfg.host == 'broker.example.com'
        assert cfg.port == 8883
        assert cfg.keepalive == 120
        assert cfg.topic == 'sensors/+/data'
        assert cfg.qos == 2
        assert cfg.client_id == 'my-client'
        assert cfg.username == 'admin'
        assert cfg.password == 'secret'
        assert cfg.min_reconnect_delay == 5
        assert cfg.max_reconnect_delay == 300

    def test_frozen_instance_cannot_be_modified(self):
        """Test that frozen dataclass raises on attribute assignment."""
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test',
        )
        with pytest.raises(FrozenInstanceError):
            cfg.host = 'changed'

    def test_port_is_int(self):
        """Test that port and numeric fields are integers."""
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=0,
            client_id='test',
            min_reconnect_delay=1,
            max_reconnect_delay=120,
        )
        assert isinstance(cfg.port, int)
        assert isinstance(cfg.keepalive, int)
        assert isinstance(cfg.qos, int)
        assert isinstance(cfg.min_reconnect_delay, int)
        assert isinstance(cfg.max_reconnect_delay, int)

    def test_frozen_rejects_arbitrary_attributes(self):
        """Test that frozen dataclass does not allow new attributes."""
        cfg = MqttConfig(
            host='localhost',
            port=1883,
            keepalive=60,
            topic='test',
            qos=1,
            client_id='test',
        )
        with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
            cfg.nonexistent_attribute = 'value'
