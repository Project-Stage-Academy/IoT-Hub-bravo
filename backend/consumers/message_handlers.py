from typing import Any, Protocol


class KafkaPayloadHandler(Protocol):
    def handle(self, payload: Any) -> None: ...


class CeleryPayloadHandler:
    def __init__(self, task, source: str = 'unknown'):
        self._task = task
        self._source = source

    def handle(self, payload: Any) -> None:
        self._task.delay(payload, source=self._source)
