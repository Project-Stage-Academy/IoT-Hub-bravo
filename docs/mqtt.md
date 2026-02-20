# MQTT Telemetry Ingestion

## Overview
This project supports real-time telemetry ingestion over MQTT using a 
Mosquitto broker and an MQTT adapter service (Paho MQTT client).
The adapter subscribes to a configured topic, validates incoming JSON 
payloads, and forwards messages to a handler (currently Celery task).


## Data Flow
Device/Publisher → Mosquitto → mqtt-adapter → MessageHandler → downstream (Celery)

Notes:
- Effective delivery QoS = min(publish QoS, subscribe QoS).
- `retain=true` messages are delivered as retained only to new subscribers (e.g., after adapter restart).


## Local Setup (Docker Compose)
1. Copy env template:
   - `cp .env.example .env` and adjust values if needed.
2. Start services:
   - `./scripts/up.sh` or `docker compose up -d --build`
3. Observe logs:
   - `./scripts/logs.sh mqtt-adapter` or `docker compose logs -f mqtt-adapter`


## Configuration
MQTT adapter configuration is driven by environment variables (see `.env.example`):

- `MQTT_HOST` – broker hostname (Compose service name in dev)
- `MQTT_PORT` – broker port (default 1883)
- `MQTT_TOPIC` – subscription topic (e.g., `telemetry`)
- `MQTT_QOS` – subscribe QoS (0/1/2). Delivery QoS is limited by subscription QoS.
- `MQTT_KEEPALIVE` – keepalive seconds
- `MQTT_CLIENT_ID` – MQTT client id
- `MQTT_USERNAME`, `MQTT_PASSWORD` – broker authentication
- `MQTT_MIN_RECONNECT_DELAY`, `MQTT_MAX_RECONNECT_DELAY` – reconnect backoff


## Connection Handling
The adapter uses `connect_async()` + `loop_forever(retry_first_connection=True)` 
and reconnect backoff via `reconnect_delay_set()`.
Handlers must be fast/non-blocking; long operations should be performed asynchronously.


## Security Considerations
Dev:
- Keep broker bound to internal Docker network.
- Use username/password in `.env` for local testing.

Prod:
- Disable anonymous access.
- Use Mosquitto ACLs to restrict device publish/subscribe topics.
- Prefer TLS, ideally mTLS for device authentication.
