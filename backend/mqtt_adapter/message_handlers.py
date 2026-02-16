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
    """
    Handles decoded MQTT JSON messages.

    This handler is invoked from the Paho MQTT client loop thread.
    Implementations must be fast / non-blocking.
    """

    def handle(self, message: MQTTJsonMessage) -> None: ...


class CeleryMessageHandler:
    def __init__(self, celery_task):
        self._task = celery_task

    def handle(self, message: MQTTJsonMessage) -> None:
        self._task.delay(
            message.payload,
            topic=message.topic,
            qos=message.qos,
            retain=message.retain,
        )
