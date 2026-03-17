import pytest
from unittest.mock import Mock, call
from dataclasses import FrozenInstanceError

from mqtt_adapter.message_handlers import (
    MQTTJsonMessage,
    CeleryMessageHandler,
    KafkaProducerMessageHandler,
)

# ──────────────────────────────────────────────
#  MQTTJsonMessage
# ──────────────────────────────────────────────


class TestMQTTJsonMessage:
    """Unit tests for MQTTJsonMessage dataclass."""

    def test_stores_all_fields(self):
        """Test that all fields are stored correctly."""
        msg = MQTTJsonMessage(
            topic='telemetry',
            qos=1,
            retain=False,
            payload={'device': 'DEV-001'},
        )
        assert msg.topic == 'telemetry'
        assert msg.qos == 1
        assert msg.retain is False
        assert msg.payload == {'device': 'DEV-001'}

    def test_list_payload(self):
        """Test message with list payload."""
        payload = [{'a': 1}, {'b': 2}]
        msg = MQTTJsonMessage(topic='t', qos=0, retain=False, payload=payload)
        assert msg.payload == payload
        assert isinstance(msg.payload, list)

    def test_frozen_instance(self):
        """Test that frozen dataclass raises on modification."""
        msg = MQTTJsonMessage(topic='t', qos=0, retain=False, payload={})
        with pytest.raises(FrozenInstanceError):
            msg.topic = 'changed'


# ──────────────────────────────────────────────
#  CeleryMessageHandler
# ──────────────────────────────────────────────


class TestCeleryMessageHandler:
    """Unit tests for CeleryMessageHandler."""

    def test_calls_task_delay(self):
        """Test handle() calls task.delay()."""
        task = Mock()
        handler = CeleryMessageHandler(task)

        msg = MQTTJsonMessage(
            topic='telemetry',
            qos=1,
            retain=False,
            payload={'device': 'DEV-001'},
        )
        handler.handle(msg)

        task.delay.assert_called_once()

    def test_passes_payload_and_metadata(self):
        """Test handle() passes payload + topic/qos/retain as kwargs."""
        task = Mock()
        handler = CeleryMessageHandler(task)

        msg = MQTTJsonMessage(
            topic='sensors/temp',
            qos=2,
            retain=True,
            payload={'temp': 22.5},
        )
        handler.handle(msg)

        task.delay.assert_called_once_with(
            {'temp': 22.5},
            topic='sensors/temp',
            qos=2,
            retain=True,
        )

    def test_list_payload_passed_correctly(self):
        """Test handle() passes list payload to delay."""
        task = Mock()
        handler = CeleryMessageHandler(task)

        payload = [{'a': 1}, {'b': 2}]
        msg = MQTTJsonMessage(topic='t', qos=0, retain=False, payload=payload)
        handler.handle(msg)

        actual_payload = task.delay.call_args.args[0]
        assert actual_payload == payload
        assert isinstance(actual_payload, list)


# ──────────────────────────────────────────────
#  KafkaProducerMessageHandler
# ──────────────────────────────────────────────


class TestKafkaProducerMessageHandler:
    """Unit tests for KafkaProducerMessageHandler."""

    @pytest.fixture
    def mock_producer(self):
        return Mock()

    def test_dict_payload_with_key_field(self, mock_producer):
        """Test dict payload extracts key from specified field."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field='device_id')

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload={'device_id': 'DEV-001', 'temp': 25},
        )
        handler.handle(msg)

        mock_producer.produce.assert_called_once_with(
            payload={'device_id': 'DEV-001', 'temp': 25},
            key='DEV-001',
        )

    def test_dict_payload_without_key_field(self, mock_producer):
        """Test dict payload with no key_field produces key=None."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field=None)

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload={'temp': 25},
        )
        handler.handle(msg)

        mock_producer.produce.assert_called_once_with(
            payload={'temp': 25},
            key=None,
        )

    def test_dict_payload_missing_key_field_value(self, mock_producer):
        """Test dict payload where key_field is not in payload returns key=None."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field='device_id')

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload={'temp': 25},
        )
        handler.handle(msg)

        mock_producer.produce.assert_called_once_with(
            payload={'temp': 25},
            key=None,
        )

    def test_list_payload_produces_each_item(self, mock_producer):
        """Test list payload calls produce for each dict item."""
        handler = KafkaProducerMessageHandler(mock_producer)

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload=[{'a': 1}, {'b': 2}, {'c': 3}],
        )
        handler.handle(msg)

        assert mock_producer.produce.call_count == 3

    def test_list_payload_extracts_keys(self, mock_producer):
        """Test list payload extracts key from each record."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field='id')

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload=[{'id': 'A', 'v': 1}, {'id': 'B', 'v': 2}],
        )
        handler.handle(msg)

        assert mock_producer.produce.call_count == 2
        calls = mock_producer.produce.call_args_list
        assert calls[0] == call(payload={'id': 'A', 'v': 1}, key='A')
        assert calls[1] == call(payload={'id': 'B', 'v': 2}, key='B')

    def test_list_payload_skips_non_dict_items(self, mock_producer):
        """Test list payload skips non-dict items."""
        handler = KafkaProducerMessageHandler(mock_producer)

        msg = MQTTJsonMessage(
            topic='t',
            qos=1,
            retain=False,
            payload=[{'a': 1}, 'not-a-dict', 42, {'b': 2}],
        )
        handler.handle(msg)

        assert mock_producer.produce.call_count == 2

    def test_list_payload_logs_warning_on_skipped_items(self, mock_producer, caplog):
        """Test that skipping non-dict items logs a warning."""
        handler = KafkaProducerMessageHandler(mock_producer)

        msg = MQTTJsonMessage(
            topic='telemetry',
            qos=1,
            retain=False,
            payload=[{'a': 1}, 'skip-me', 42],
        )

        import logging

        with caplog.at_level(logging.WARNING, logger='mqtt_adapter.message_handlers'):
            handler.handle(msg)

        assert mock_producer.produce.call_count == 1
        assert 'skipped=2' in caplog.text

    def test_extract_key_returns_none_when_no_key_field(self, mock_producer):
        """Test _extract_key returns None when key_field is None."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field=None)
        result = handler._extract_key({'device_id': 'DEV-001'})
        assert result is None

    def test_extract_key_returns_none_when_field_missing(self, mock_producer):
        """Test _extract_key returns None when field not in payload."""
        handler = KafkaProducerMessageHandler(mock_producer, key_field='missing')
        result = handler._extract_key({'device_id': 'DEV-001'})
        assert result is None
