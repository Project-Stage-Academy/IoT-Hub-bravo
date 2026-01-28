import argparse
import json
import time
import uuid
import random
from datetime import datetime, timezone

import requests
import paho.mqtt.publish as publish


def build_payload(device, schema_version, template):
    return {
        "schema_version": schema_version,
        "device": device,
        "ts": datetime.now(timezone.utc).isoformat(),
        "metrics": [
            {
                "metric": k,
                "t": v["t"],
                "v": eval(v["v"]),
            }
            for k, v in template.items()
        ],
    }


def send_http(url, payload):
    r = requests.post(url, json=payload, timeout=5)
    return r.status_code, r.text


def send_mqtt(broker, topic, payload):
    publish.single(topic, json.dumps(payload), hostname=broker)
    return "published", topic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["http", "mqtt"], required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--rate", type=float, default=1)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--schema-version", type=int, default=1)

    parser.add_argument("--http-url", default="http://localhost:8000/api/telemetry/")
    parser.add_argument("--mqtt-broker", default="localhost")
    parser.add_argument("--mqtt-topic", default="telemetry")

    args = parser.parse_args()

    payload_template = {
        "temperature": {"t": "numeric", "v": "round(random.uniform(20,30),2)"},
        "is_online": {"t": "bool", "v": "True"},
    }

    for i in range(args.count):
        payload = build_payload(
            args.device, args.schema_version, payload_template
        )

        if args.mode == "http":
            status, resp = send_http(args.http_url, payload)
        else:
            status, resp = send_mqtt(
                args.mqtt_broker, args.mqtt_topic, payload
            )

        print(f"[{i+1}] status={status} response={resp}")
        time.sleep(args.rate)


if __name__ == "__main__":
    main()
