import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import paho.mqtt.client as mqtt

from .config import MqttConfig
from .message_handlers import MQTTJsonMessage, MessageHandler

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MqttCallbacks:
    """
    Container for Paho MQTT client callbacks.
    Subscribes to the configured topic on successful connect;
    Decodes JSON payload and passes it to MessageHandler instance;
    Rejects malformed/non-JSON messages.
    """

    config: MqttConfig
    handler: MessageHandler

    def on_connect(self, c: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int) -> None:
        if rc != 0:
            logger.error(
                'MQTT connect failed: rc=%s host=%s port=%s',
                rc,
                self.config.host,
                self.config.port,
            )
            return

        logger.info(
            'Connected to MQTT broker %s:%s. Subscribing to topic=%s qos=%s',
            self.config.host,
            self.config.port,
            self.config.topic,
            self.config.qos,
        )
        c.subscribe(self.config.topic, qos=self.config.qos)

    def on_disconnect(self, c: mqtt.Client, userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning('Unexpected MQTT disconnect: rc=%s', rc)
        else:
            logger.info('MQTT disconnected.')

    def on_message(self, c: mqtt.Client, userdata: Any, m: mqtt.MQTTMessage) -> None:
        obj = self._payload_to_json(m.payload)

        if obj is None:
            logger.warning('Invalid JSON object rejected.', extra=self._extra(m))
            return

        logger.info('MQTT message received.', extra=self._extra(m))

        message = MQTTJsonMessage(
            topic=m.topic,
            qos=m.qos,
            retain=bool(m.retain),
            payload=obj,
        )

        try:
            self.handler.handle(message)
        except Exception:
            logger.exception('Failed to handle MQTT message: ', extra=self._extra(m))

    @staticmethod
    def _payload_to_json(payload: bytes) -> dict | list | None:
        try:
            text = payload.decode('utf-8')
            obj = json.loads(text)
            return obj if isinstance(obj, (dict, list)) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _extra(m: mqtt.MQTTMessage) -> dict[str, Any]:
        """Helper method for logging."""
        return {
            'topic': m.topic,
            'qos': m.qos,
            'retain': bool(m.retain),
            'payload_len': len(m.payload),
        }


def _normalize_credential(credential: str) -> Optional[str]:
    normalized = credential.strip()
    return normalized if normalized else None


def apply_mqtt_auth(client: mqtt.Client, config: MqttConfig) -> None:
    username = _normalize_credential(config.username)
    password = _normalize_credential(config.password)

    if username is None:
        raise ValueError('Invalid MQTT_USERNAME value.')
    if password is None:
        raise ValueError('Invalid MQTT_PASSWORD value.')

    client.username_pw_set(username, password)


def build_client(config: MqttConfig, callbacks: MqttCallbacks) -> mqtt.Client:
    client = mqtt.Client(client_id=config.client_id)
    apply_mqtt_auth(client=client, config=config)

    client.on_connect = callbacks.on_connect
    client.on_disconnect = callbacks.on_disconnect
    client.on_message = callbacks.on_message

    client.reconnect_delay_set(
        min_delay=config.min_reconnect_delay,
        max_delay=config.max_reconnect_delay,
    )
    return client


def run_mqtt_client(*, config: MqttConfig, handler: MessageHandler) -> None:
    callbacks = MqttCallbacks(config=config, handler=handler)
    client = build_client(config, callbacks)

    logger.info('Connecting to MQTT broker %s:%s...', config.host, config.port)
    client.connect_async(config.host, config.port, keepalive=config.keepalive)
    client.loop_forever(retry_first_connection=True)
