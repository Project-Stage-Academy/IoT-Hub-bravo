from typing import Any, Protocol


class KafkaPayloadHandler(Protocol):
    def handle(self, payload: Any) -> None: ...


class CeleryPayloadHandler:
    def __init__(self, task):
        self._task = task

    def handle(self, payload: Any) -> None:
        self._task.delay(payload)


class TelemetryPayloadHandler(CeleryPayloadHandler):
    """Injects source label for observability metrics."""

    def __init__(self, task, source: str = 'unknown'):
        super().__init__(task)
        self._source = source

    def handle(self, payload: Any) -> None:
        self._task.delay(payload, source=self._source)
