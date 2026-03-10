from unittest.mock import patch, Mock

from consumers.telemetry_writer import main


class TestTelemetryWriterMain:
    """Tests for telemetry_writer.main() entrypoint wiring."""

    @patch('consumers.telemetry_writer.signal.signal')
    @patch('consumers.telemetry_writer.KafkaConsumer')
    @patch('consumers.telemetry_writer.setup_logging')
    def test_main_creates_consumer_and_starts(
        self,
        mock_logging,
        mock_consumer_cls,
        mock_signal,
    ):
        """Test main() creates KafkaConsumer and calls start()."""
        mock_consumer = Mock()
        mock_consumer_cls.return_value = mock_consumer

        main()

        mock_consumer_cls.assert_called_once()
        mock_consumer.start.assert_called_once()

    @patch('consumers.telemetry_writer.signal.signal')
    @patch('consumers.telemetry_writer.KafkaConsumer')
    @patch('consumers.telemetry_writer.setup_logging')
    def test_main_registers_signal_handlers(
        self,
        mock_logging,
        mock_consumer_cls,
        mock_signal,
    ):
        """Test main() registers SIGTERM and SIGINT handlers."""
        import signal

        mock_consumer = Mock()
        mock_consumer_cls.return_value = mock_consumer

        main()

        signal_calls = mock_signal.call_args_list
        registered_signals = {c.args[0] for c in signal_calls}
        assert signal.SIGTERM in registered_signals
        assert signal.SIGINT in registered_signals

    @patch('consumers.telemetry_writer.signal.signal')
    @patch('consumers.telemetry_writer.KafkaConsumer')
    @patch('consumers.telemetry_writer.setup_logging')
    def test_main_passes_celery_handler(
        self,
        mock_logging,
        mock_consumer_cls,
        mock_signal,
    ):
        """Test main() passes CeleryPayloadHandler as handler."""
        from consumers.message_handlers import CeleryPayloadHandler

        mock_consumer = Mock()
        mock_consumer_cls.return_value = mock_consumer

        main()

        kwargs = mock_consumer_cls.call_args.kwargs
        assert isinstance(kwargs['handler'], CeleryPayloadHandler)
