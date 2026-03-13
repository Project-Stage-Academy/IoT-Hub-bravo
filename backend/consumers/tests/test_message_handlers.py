from unittest.mock import Mock

from consumers.message_handlers import CeleryPayloadHandler, TelemetryPayloadHandler


class TestCeleryPayloadHandler:
    """Unit tests for CeleryPayloadHandler (generic, no source)."""

    def test_handle_calls_task_delay_with_dict_payload(self):
        task = Mock()
        handler = CeleryPayloadHandler(task)
        payload = {'device_id': 'DEV-001', 'temperature': 25.5}
        handler.handle(payload)
        task.delay.assert_called_once_with(payload)

    def test_handle_calls_task_delay_with_list_payload(self):
        task = Mock()
        handler = CeleryPayloadHandler(task)
        payload = [{'device_id': 'DEV-001'}, {'device_id': 'DEV-002'}]
        handler.handle(payload)
        task.delay.assert_called_once_with(payload)

    def test_stores_task_reference(self):
        task = Mock()
        handler = CeleryPayloadHandler(task)
        assert handler._task is task

    def test_conforms_to_protocol_structurally(self):
        task = Mock()
        handler = CeleryPayloadHandler(task)
        assert hasattr(handler, 'handle')
        assert callable(handler.handle)

    def test_handle_passes_payload_unchanged(self):
        task = Mock()
        handler = CeleryPayloadHandler(task)
        payload = {'key': 'value', 'nested': {'a': 1}}
        handler.handle(payload)
        actual = task.delay.call_args.args[0]
        assert actual is payload


class TestTelemetryPayloadHandler:
    """Unit tests for TelemetryPayloadHandler (injects source)."""

    def test_default_source_is_unknown(self):
        task = Mock()
        handler = TelemetryPayloadHandler(task)
        handler.handle({'data': 1})
        task.delay.assert_called_once_with({'data': 1}, source='unknown')

    def test_custom_source_passed(self):
        task = Mock()
        handler = TelemetryPayloadHandler(task, source='kafka')
        handler.handle({'data': 1})
        task.delay.assert_called_once_with({'data': 1}, source='kafka')

    def test_inherits_from_celery_handler(self):
        handler = TelemetryPayloadHandler(Mock(), source='mqtt')
        assert isinstance(handler, CeleryPayloadHandler)
