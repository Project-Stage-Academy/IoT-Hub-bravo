# #!/usr/bin/env python3
import requests
import json
import paho.mqtt.client as mqtt

MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "telemetry"
HTTP_URL = "http://localhost:8000/api/telemetry/"


def on_connect(client, userdata, flags, rc):
    print(
        f"--- Connected to MQTT broker with result code {rc} ---\n --- Use Ctrl+C to stop subscriber ---"
    )
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        print(f"Received message on {msg.topic}: {payload}")

        # Forward to HTTP endpoint
        r = requests.post(HTTP_URL, json=payload, timeout=5)
        if r.status_code in (200, 201):
            print(f"Forwarded to {HTTP_URL} (HTTP {r.status_code})")
        else:
            print(f"HTTP {r.status_code} response: {r.text}")

    except json.JSONDecodeError:
        print("Received invalid JSON")
    except requests.RequestException as e:
        print(f"Failed to forward to HTTP endpoint: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, 1883, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down MQTT subscriber...")
        client.disconnect()
        print("--- Subscriber stopped gracefully ---")


if __name__ == "__main__":
    main()
