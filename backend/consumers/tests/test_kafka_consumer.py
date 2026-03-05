from unittest.mock import Mock, patch

from confluent_kafka import KafkaException

from consumers.config import ConsumerConfig
from consumers.kafka_consumer import KafkaConsumer

# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────


def make_kafka_message(value=b'{"key":"val"}', error=None, offset=0):
    """Create a minimal Kafka Message mock."""
    msg = Mock()
    msg.value.return_value = value
    msg.error.return_value = error
    msg.offset.return_value = offset
    return msg


def make_consumer(
    mock_kafka_consumer,
    *,
    decode_json=False,
    consume_batch=False,
    batch_max_size=50,
    auto_commit=False,
    handler=None,
):
    """Build a KafkaConsumer with mocked confluent_kafka.Consumer."""
    config = ConsumerConfig(
        bootstrap_servers='localhost:9092',
        group_id='test-group',
        auto_offset_reset='earliest',
        enable_auto_commit=auto_commit,
    )
    if handler is None:
        handler = Mock()

    consumer = KafkaConsumer(
        config=config,
        topics=['test-topic'],
        handler=handler,
        decode_json=decode_json,
        consume_batch=consume_batch,
        batch_max_size=batch_max_size,
    )
    return consumer


# ──────────────────────────────────────────────
#  Constructor
# ──────────────────────────────────────────────


class TestKafkaConsumerInit:
    """Tests for KafkaConsumer constructor."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_batch_false_sets_consume_one(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, consume_batch=False)
        assert consumer._consume == consumer._consume_one

    @patch('consumers.kafka_consumer.Consumer')
    def test_batch_true_sets_consume_batch(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, consume_batch=True)
        assert consumer._consume == consumer._consume_batch


# ──────────────────────────────────────────────
#  _is_valid_message
# ──────────────────────────────────────────────


class TestIsValidMessage:
    """Tests for KafkaConsumer._is_valid_message static method."""

    def test_none_message_returns_false(self):
        assert KafkaConsumer._is_valid_message(None) is False

    def test_message_with_error_returns_false(self):
        msg = make_kafka_message(error=Mock())
        assert KafkaConsumer._is_valid_message(msg) is False

    def test_valid_message_returns_true(self):
        msg = make_kafka_message(error=None)
        assert KafkaConsumer._is_valid_message(msg) is True


# ──────────────────────────────────────────────
#  _decode_message
# ──────────────────────────────────────────────


class TestDecodeMessage:
    """Tests for KafkaConsumer._decode_message static method."""

    def test_valid_dict_json(self):
        msg = make_kafka_message(value=b'{"a": 1}')
        result = KafkaConsumer._decode_message(msg)
        assert result == {'a': 1}

    def test_valid_list_json(self):
        msg = make_kafka_message(value=b'[1, 2, 3]')
        result = KafkaConsumer._decode_message(msg)
        assert result == [1, 2, 3]

    def test_none_value_returns_none(self):
        msg = make_kafka_message(value=None)
        result = KafkaConsumer._decode_message(msg)
        assert result is None

    def test_invalid_json_returns_none(self):
        msg = make_kafka_message(value=b'{"broken": ')
        result = KafkaConsumer._decode_message(msg)
        assert result is None

    def test_invalid_utf8_returns_none(self):
        msg = make_kafka_message(value=b'\xff\xfe\xfd')
        result = KafkaConsumer._decode_message(msg)
        assert result is None


# ──────────────────────────────────────────────
#  _get_message_payload
# ──────────────────────────────────────────────


class TestGetMessagePayload:
    """Tests for KafkaConsumer._get_message_payload."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_decode_json_true_calls_decode(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, decode_json=True)
        msg = make_kafka_message(value=b'{"x": 1}')

        result = consumer._get_message_payload(msg)
        assert result == {'x': 1}

    @patch('consumers.kafka_consumer.Consumer')
    def test_decode_json_false_returns_raw_value(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, decode_json=False)
        raw = b'raw-bytes'
        msg = make_kafka_message(value=raw)

        result = consumer._get_message_payload(msg)
        assert result == raw


# ──────────────────────────────────────────────
#  _handle_payload
# ──────────────────────────────────────────────


class TestHandlePayload:
    """Tests for KafkaConsumer._handle_payload."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_success_returns_true(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler)

        result = consumer._handle_payload({'data': 1})

        assert result is True
        handler.handle.assert_called_once_with({'data': 1})

    @patch('consumers.kafka_consumer.Consumer')
    def test_exception_returns_false(self, mock_consumer_cls):
        handler = Mock()
        handler.handle.side_effect = ValueError('boom')
        consumer = make_consumer(mock_consumer_cls, handler=handler)

        result = consumer._handle_payload({'data': 1})

        assert result is False


# ──────────────────────────────────────────────
#  _commit
# ──────────────────────────────────────────────


class TestCommit:
    """Tests for KafkaConsumer._commit."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_manual_commit_calls_consumer_commit(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, auto_commit=False)
        msg = make_kafka_message()

        consumer._commit(msg)

        consumer._consumer.commit.assert_called_once_with(
            message=msg,
            asynchronous=False,
        )

    @patch('consumers.kafka_consumer.Consumer')
    def test_auto_commit_does_not_call_commit(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls, auto_commit=True)
        msg = make_kafka_message()

        consumer._commit(msg)

        consumer._consumer.commit.assert_not_called()


# ──────────────────────────────────────────────
#  _handle_and_commit
# ──────────────────────────────────────────────


class TestHandleAndCommit:
    """Tests for KafkaConsumer._handle_and_commit."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_success_commits(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler, auto_commit=False)
        msg = make_kafka_message()

        consumer._handle_and_commit({'data': 1}, msg)

        consumer._consumer.commit.assert_called_once()

    @patch('consumers.kafka_consumer.Consumer')
    def test_failure_does_not_commit(self, mock_consumer_cls):
        handler = Mock()
        handler.handle.side_effect = RuntimeError('fail')
        consumer = make_consumer(mock_consumer_cls, handler=handler, auto_commit=False)
        msg = make_kafka_message()

        consumer._handle_and_commit({'data': 1}, msg)

        consumer._consumer.commit.assert_not_called()


# ──────────────────────────────────────────────
#  _consume_one
# ──────────────────────────────────────────────


class TestConsumeOne:
    """Tests for KafkaConsumer._consume_one."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_happy_path(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(
            mock_consumer_cls, handler=handler, decode_json=True, auto_commit=False
        )
        msg = make_kafka_message(value=b'{"a": 1}')
        consumer._consumer.poll.return_value = msg

        consumer._consume_one()

        handler.handle.assert_called_once_with({'a': 1})
        consumer._consumer.commit.assert_called_once()

    @patch('consumers.kafka_consumer.Consumer')
    def test_none_message_skips(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler)
        consumer._consumer.poll.return_value = None

        consumer._consume_one()

        handler.handle.assert_not_called()

    @patch('consumers.kafka_consumer.Consumer')
    def test_error_message_skips(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler)
        consumer._consumer.poll.return_value = make_kafka_message(error=Mock())

        consumer._consume_one()

        handler.handle.assert_not_called()

    @patch('consumers.kafka_consumer.Consumer')
    def test_decode_failure_skips(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler, decode_json=True)
        consumer._consumer.poll.return_value = make_kafka_message(value=None)

        consumer._consume_one()

        handler.handle.assert_not_called()


# ──────────────────────────────────────────────
#  _consume_batch
# ──────────────────────────────────────────────


class TestConsumeBatch:
    """Tests for KafkaConsumer._consume_batch."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_empty_messages_returns_early(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler, consume_batch=True)
        consumer._consumer.consume.return_value = []

        consumer._consume_batch()

        handler.handle.assert_not_called()

    @patch('consumers.kafka_consumer.Consumer')
    def test_aggregates_dict_payloads(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(
            mock_consumer_cls,
            handler=handler,
            consume_batch=True,
            decode_json=True,
            auto_commit=False,
        )
        msgs = [
            make_kafka_message(value=b'{"a": 1}'),
            make_kafka_message(value=b'{"b": 2}'),
        ]
        consumer._consumer.consume.return_value = msgs

        consumer._consume_batch()

        handler.handle.assert_called_once()
        batch = handler.handle.call_args.args[0]
        assert batch == [{'a': 1}, {'b': 2}]

    @patch('consumers.kafka_consumer.Consumer')
    def test_skips_invalid_messages(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(
            mock_consumer_cls,
            handler=handler,
            consume_batch=True,
            decode_json=True,
            auto_commit=False,
        )
        msgs = [
            make_kafka_message(value=b'{"a": 1}'),
            make_kafka_message(error=Mock()),  # invalid
            make_kafka_message(value=b'{"c": 3}'),
        ]
        consumer._consumer.consume.return_value = msgs

        consumer._consume_batch()

        batch = handler.handle.call_args.args[0]
        assert batch == [{'a': 1}, {'c': 3}]

    @patch('consumers.kafka_consumer.Consumer')
    def test_extends_list_payloads(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(
            mock_consumer_cls,
            handler=handler,
            consume_batch=True,
            decode_json=True,
            auto_commit=False,
        )
        msgs = [
            make_kafka_message(value=b'[{"a": 1}, {"b": 2}]'),
            make_kafka_message(value=b'{"c": 3}'),
        ]
        consumer._consumer.consume.return_value = msgs

        consumer._consume_batch()

        batch = handler.handle.call_args.args[0]
        assert batch == [{'a': 1}, {'b': 2}, {'c': 3}]


# ──────────────────────────────────────────────
#  start / stop
# ──────────────────────────────────────────────


class TestStartStop:
    """Tests for KafkaConsumer.start and .stop."""

    @patch('consumers.kafka_consumer.Consumer')
    def test_stop_sets_running_false(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls)
        assert consumer._running is True

        consumer.stop()

        assert consumer._running is False

    @patch('consumers.kafka_consumer.Consumer')
    def test_start_calls_close_on_exit(self, mock_consumer_cls):
        consumer = make_consumer(mock_consumer_cls)
        # Make start() exit after one iteration
        consumer._running = False

        consumer.start()

        consumer._consumer.close.assert_called_once()

    @patch('consumers.kafka_consumer.Consumer')
    def test_start_catches_kafka_exception(self, mock_consumer_cls):
        handler = Mock()
        consumer = make_consumer(mock_consumer_cls, handler=handler)
        consumer._consumer.poll.side_effect = KafkaException('crash')

        # Should not raise
        consumer.start()

        consumer._consumer.close.assert_called_once()
