import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import paho.mqtt.client as mqtt

from .config import MqttConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MqttCallbacks:
    """
    Container for Paho MQTT client callbacks.
    Subscribes to the configured topic on successful connect;
    Decodes JSON payloads and pass them to `handle_payload`;
    Rejects malformed/non-JSON messages.
    """

    config: MqttConfig
    handle_payload: Callable

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
            logger.info('MQTT disconnected')

    def on_message(self, c: mqtt.Client, userdata: Any, m: mqtt.MQTTMessage) -> None:
        obj = self._payload_to_json(m.payload)
        if obj is None:
            logger.warning(
                'Invalid JSON object rejected: '
                'topic=%s qos=%s retain=%s payload_type=%s payload_len=%s',
                m.topic,
                m.qos,
                bool(m.retain),
                type(obj).__name__,
                len(m.payload),
            )
            return

        logger.info(
            'MQTT message received: topic=%s qos=%s retain=%s payload_type=%s payload_len=%s',
            m.topic,
            m.qos,
            bool(m.retain),
            type(obj).__name__,
            len(m.payload),
        )

        try:
            self.handle_payload(obj)
        except Exception:
            logger.exception(
                'Failed to handle MQTT message: '
                'topic=%s qos=%s retain=%s payload_type=%s payload_len=%s',
                m.topic,
                m.qos,
                bool(m.retain),
                type(obj).__name__,
                len(m.payload),
            )

    @staticmethod
    def _payload_to_json(payload: bytes) -> dict | list | None:
        try:
            text = payload.decode('utf-8')
            obj = json.loads(text)
            return obj if isinstance(obj, (dict, list)) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None


def build_client(config: MqttConfig, callbacks: MqttCallbacks) -> mqtt.Client:
    client = mqtt.Client(client_id=config.client_id)
    client.username_pw_set(config.username, config.password)

    client.on_connect = callbacks.on_connect
    client.on_disconnect = callbacks.on_disconnect
    client.on_message = callbacks.on_message

    client.reconnect_delay_set(
        min_delay=config.min_reconnect_delay,
        max_delay=config.max_reconnect_delay,
    )
    return client


def run_mqtt_client(*, config: MqttConfig, handle_payload: Callable) -> None:
    callbacks = MqttCallbacks(config=config, handle_payload=handle_payload)
    client = build_client(config, callbacks)

    logger.info('Connecting to MQTT broker %s:%s...', config.host, config.port)
    client.connect_async(config.host, config.port, keepalive=config.keepalive)
    client.loop_forever(retry_first_connection=True)
