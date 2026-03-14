from unittest.mock import Mock

from consumers.message_handlers import CeleryPayloadHandler


class TestCeleryPayloadHandler:
    """Unit tests for CeleryPayloadHandler."""

    def test_handle_calls_task_delay_with_dict_payload(self):
        """Test handle() calls task.delay() with a dict payload."""
        task = Mock()
        handler = CeleryPayloadHandler(task)

        payload = {'device_id': 'DEV-001', 'temperature': 25.5}
        handler.handle(payload)

        task.delay.assert_called_once_with(payload)

    def test_handle_calls_task_delay_with_list_payload(self):
        """Test handle() calls task.delay() with a list payload."""
        task = Mock()
        handler = CeleryPayloadHandler(task)

        payload = [{'device_id': 'DEV-001'}, {'device_id': 'DEV-002'}]
        handler.handle(payload)

        task.delay.assert_called_once_with(payload)

    def test_stores_task_reference(self):
        """Test that constructor stores the task internally."""
        task = Mock()
        handler = CeleryPayloadHandler(task)

        assert handler._task is task

    def test_conforms_to_protocol_structurally(self):
        """Test CeleryPayloadHandler has handle() method matching the protocol."""
        task = Mock()
        handler = CeleryPayloadHandler(task)

        assert hasattr(handler, 'handle')
        assert callable(handler.handle)

    def test_handle_passes_payload_unchanged(self):
        """Test that handle() passes the exact object to delay without modification."""
        task = Mock()
        handler = CeleryPayloadHandler(task)

        payload = {'key': 'value', 'nested': {'a': 1}}
        handler.handle(payload)

        actual = task.delay.call_args.args[0]
        assert actual is payload
