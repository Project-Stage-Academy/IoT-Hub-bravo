from dataclasses import dataclass

from decouple import config


@dataclass(frozen=True, slots=True)
class MqttConfig:
    host: str = config("MQTT_HOST", default="mosquitto")
    port: int = config("MQTT_PORT", default="1883", cast=int)
    keepalive: int = config("MQTT_KEEPALIVE", default="60", cast=int)
    topic: str = config("MQTT_TOPIC", default="telemetry")
    qos: int = config("MQTT_QOS", default="1", cast=int)
    client_id: str = config("MQTT_CLIENT_ID", default="iot-hub-mqtt-adapter")
    username: str = config("MQTT_USERNAME", "change-me-username-insecure")
    password: str = config("MQTT_PASSWORD", "change-me-password-insecure")
    min_reconnect_delay: int = config("MQTT_MIN_RECONNECT_DELAY", default="1", cast=int)
    max_reconnect_delay: int = config(
        "MQTT_MAX_RECONNECT_DELAY", default="120", cast=int
    )
