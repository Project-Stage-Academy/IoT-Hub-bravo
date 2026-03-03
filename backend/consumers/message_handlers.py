from typing import Any, Protocol


class KafkaPayloadHandler(Protocol):
    def handle(self, payload: Any) -> None: ...


class CeleryPayloadHandler:
    def __init__(self, task):
        self._task = task

    def handle(self, payload: Any) -> None:
        self._task.delay(payload)
