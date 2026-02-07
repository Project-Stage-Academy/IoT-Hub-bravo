from dataclasses import dataclass
from decouple import config


@dataclass(frozen=True, slots=True)
class MqttConfig:
    host: str = config('MQTT_HOST', default='mosquitto')
    port: int = config('MQTT_PORT', default='1883', cast=int)
    keepalive: int = config('MQTT_KEEPALIVE', default='60', cast=int)
    topic: str = config('MQTT_TOPIC', default='telemetry')
    qos: int = config('MQTT_QOS', default='1', cast=int)
    client_id: str = config('MQTT_CLIENT_ID', default='iot-hub-mqtt-adapter')
