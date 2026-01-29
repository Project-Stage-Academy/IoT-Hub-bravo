import argparse
import json
import random
import time
from datetime import datetime, timezone

import requests
import paho.mqtt.publish as publish

import os
import sys
from pathlib import Path

# Add project root to sys.path for Django apps import
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")


import django
django.setup()

from apps.devices.models import Device, DeviceMetric

def prompt(msg):
    """Prompt dev for input and return the stripped string"""
    return input(msg).strip()


def parse_value(value, data_type):
    """Convert input value to the correct data type"""
    if data_type == "numeric":
        return float(value)
    if data_type == "bool":
        return value.lower() in ("true", "false", "1", "0")
    return value

class ManualProvider:
    """Data provider that requests input from the dev manually"""
    def __init__(self, device_metric):
        self.device_metric = device_metric

    def get(self):
        metric = self.device_metric.metric
        value = prompt(
            f"Enter value for {metric.metric_type} ({metric.data_type}): "
        )
        return parse_value(value, metric.data_type)


class RandomProvider:
    """Data provider that generates random values"""
    def __init__(self, device_metric):
        self.metric = device_metric.metric
        self.rule = self._configure()

    def _configure(self):
        """Configure the value generator based on metric type"""
        t = self.metric.data_type
        name = self.metric.metric_type

        if t == "numeric":
            min_v = float(prompt(f"{name} min: "))
            max_v = float(prompt(f"{name} max: "))
            return lambda: round(random.uniform(min_v, max_v), 2)

        if t == "bool":
            return lambda: random.choice([True, False])

         # For other types, dev provides a list of possible values
        values = prompt(f"{name} values (comma-separated): ").split(",")
        values = [v.strip() for v in values if v.strip()]
        return lambda: random.choice(values)

    def get(self):
        return self.rule()

    
def send_http(url, payload):
    """Send telemetry payload via HTTP POST"""
    r = requests.post(url, json=payload, timeout=5)
    return r.status_code, r.text


def send_mqtt(broker, topic, payload):
    """Send telemetry payload via MQTT"""
    publish.single(topic, json.dumps(payload), hostname=broker)
    return "published", topic


def main():
    parser = argparse.ArgumentParser(description="IoT Telemetry Simulator")
    parser.add_argument("--mode", choices=["http", "mqtt"], required=True, help="Data sending mode http/mqtt")
    parser.add_argument("--device", required=True, help="Device serial ID")
    parser.add_argument("--rate", type=float, default=1, help="Messages per second")
    parser.add_argument("--count", type=int, default=1, help="Number of messages to send")
    parser.add_argument("--schema-version", type=int, default=1, help="Message schema version")
    parser.add_argument("--value-generation", choices=["manual", "random"], required=True, help="Metric value generation mode manual/random")
    parser.add_argument("--http-url", default="http://localhost:8000/api/telemetry/", help="HTTP endpoint URL")
    parser.add_argument("--mqtt-broker", default="mosquitto", help="MQTT broker hostname")
    parser.add_argument("--mqtt-topic", default="telemetry", help="MQTT topic to publish to")

    args = parser.parse_args()

    # Log parser arguments for debugging
    print("Parsed arguments:", vars(args))

    try:
        device = Device.objects.get(serial_id=args.device)
    except Device.DoesNotExist:
        print(f"Device with serial_id '{args.device}' does not exist.")
        return
    
    # Fetch all metrics for the device
    device_metrics = (
        DeviceMetric.objects
        .select_related("metric")
        .filter(device=device)
    )

    if not device_metrics.exists():
        print("Device has no metrics configured")
        return

    # Choose provider class based on value-generation mode
    Provider = ManualProvider if args.value_generation == "manual" else RandomProvider
    providers = {}

    # Configure each metric with its provider
    for dm in device_metrics:
        print(f"\nConfiguring {dm.metric.metric_type}")
        providers[dm.metric.metric_type] = Provider(dm)

    # Calculate delay between messages based on rate
    delay = 1 / args.rate

    # Send telemetry messages
    for i in range(args.count):
        metrics_payload = {
            name: provider.get()
            for name, provider in providers.items()
        }

        payload = {
            "schema_version": 1,
            "device": device.serial_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics_payload,
        }

        try:
            if args.mode == "http":
                status = send_http(args.http_url, payload)
            else:
                status = send_mqtt(args.mqtt_broker, args.mqtt_topic, payload)

            print(f"[{i+1}/{args.count}] sent ({status})")

        except Exception as e:
            print(f"[{i+1}/{args.count}] failed: {e}")

        time.sleep(delay)


if __name__ == "__main__":
    main()
