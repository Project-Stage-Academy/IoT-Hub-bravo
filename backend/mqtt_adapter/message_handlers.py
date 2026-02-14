from typing import Any, Protocol
from dataclasses import dataclass

JsonPayload = dict[str, Any] | list[Any]


@dataclass(frozen=True, slots=True)
class MQTTJsonMessage:
    topic: str
    qos: int
    retain: bool
    payload: JsonPayload


class MessageHandler(Protocol):
    def handle(self, message: MQTTJsonMessage) -> None:
        """Must be fast / non-blocking."""
        pass


class CeleryMessageHandler:
    def __init__(self, celery_task):
        self._task = celery_task

    def handle(self, message: MQTTJsonMessage) -> None:
        self._task.delay(message.payload)
