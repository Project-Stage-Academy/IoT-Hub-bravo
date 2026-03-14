import pytest
from unittest.mock import Mock

from mqtt_adapter.config import MqttConfig
from mqtt_adapter.message_handlers import MessageHandler


@pytest.fixture
def mqtt_config():
    return MqttConfig(
        host='localhost',
        port=1883,
        keepalive=60,
        topic='telemetry',
        qos=1,
        client_id='test-client',
        username='test-user',
        password='test-pass',
        min_reconnect_delay=1,
        max_reconnect_delay=120,
    )


@pytest.fixture
def mock_message_handler():
    return Mock(spec=MessageHandler)
