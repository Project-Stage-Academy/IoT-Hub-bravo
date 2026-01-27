import time
import json
import random
import argparse
import logging
from jinja2 import Template

# HTTP / MQTT
import requests
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ACTIONS = ["login", "logout", "purchase", "view_page"]

PAYLOAD_TEMPLATE = """
{
    "schema_version": "v1",
    "serial_id": "{{ serial_id }}",
    "ts": "{{ timestamp }}",
    "value": {{ value }},
    "metric_type": "{{ metric_type }}"
}
"""

def render_payload(serial_id, metric_type):
    context = {
        "serial_id": serial_id,
        "metric_type": metric_type,
        "value": round(random.uniform(20, 100), 2),
        "timestamp": int(time.time())
    }
    rendered = Template(PAYLOAD_TEMPLATE).render(**context)
    return json.loads(rendered)

def send_http(url, payload):
    r = requests.post(url, json=payload)
    logging.info("HTTP POST %s → %s %s", url, r.status_code, r.text)

def send_mqtt(broker, topic, payload, client=None):
    if client is None:
        client = mqtt.Client()
        client.connect(broker)
    client.publish(topic, json.dumps(payload))
    logging.info("MQTT PUBLISH %s → %s", topic, payload)
    return client

def main():
    parser = argparse.ArgumentParser(description="Telemetry Simulator")
    parser.add_argument("--mode", choices=["http", "mqtt"], default="http", help="Transport mode")
    parser.add_argument("--device", required=True, help="Device serial id")
    parser.add_argument("--metric-type", default="temperature", help="Metric type")
    parser.add_argument("--rate", type=float, default=1, help="Messages per second")
    parser.add_argument("--count", type=int, default=0, help="Number of messages (0 = infinite)")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/telemetry/", help="HTTP endpoint")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker")
    parser.add_argument("--mqtt-topic", default="telemetry", help="MQTT topic")
    args = parser.parse_args()

    interval = 1 / args.rate
    logging.info("Simulator started: mode=%s device=%s rate=%.2f/s count=%d",
                 args.mode, args.device, args.rate, args.count)

    mqtt_client = None
    if args.mode == "mqtt":
        mqtt_client = mqtt.Client()
        mqtt_client.connect(args.mqtt_broker)

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            payload = render_payload(args.device, args.metric_type)
            if args.mode == "http":
                send_http(args.url, payload)
            else:
                send_mqtt(args.mqtt_broker, args.mqtt_topic, payload, mqtt_client)
            sent += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Simulator stopped manually after %d messages", sent)

if __name__ == "__main__":
    main()
