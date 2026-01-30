# IoT Telemetry Simulator

Generate and send simulated telemetry data for development and testing. Supports HTTP and MQTT transport with manual or random value generation.

---

## Table of Contents

- [Requirements](#requirements)

- [Running the Simulator](#running-the-simulator)

- [Manual vs Random Modes](#manual-vs-random-modes)

- [Payload Structure](#payload-structure)

- [Example Prompts](#example-prompts)


---

## Requirements

- Docker Compose running `web` and `db`. For MQTT mode, start `mosquitto` too.
- Seeded data so devices/metrics exist (see [Running the Simulator](#running-the-simulator)).

---

## Running the Simulator

1. Start the stack:

    ```bash
    docker compose up -d
    ```

2. Seed sample data (required):

    ```bash
    docker compose exec web python manage.py seed_dev_data
    ```

3. Run the simulator:

### HTTP mode
```bash
# HTTP mode, random values, device SN-A1-TEMP-0001, 10 messages, 1 message per second
docker compose exec web python simulator/run.py \
    --mode http \
    --device SN-A1-TEMP-0001 \
    --rate 1 \
    --count 10 \
    --value-generation random
```

 ### MQTT mode
In this mode, the simulator publishes telemetry messages to MQTT, while a separate MQTT forwarder subscribes to MQTT topics and forwards messages to the backend via HTTP.

> [!IMPORTANT]
The MQTT forwarder must be started in a separate terminal.
If it is not running, MQTT messages will be published but will not reach the backend.

1. Start MQTT → HTTP forwarder
```bash
docker compose exec web python simulator/mqtt_forwarder.py
```

2. Run simulator in MQTT mode
```bash
# MQTT mode, manual values, device SN-A1-TEMP-0001, 10 messages, 1 message per second
docker compose exec web python simulator/run.py \
    --mode mqtt \
    --device SN-A1-TEMP-0001 \
    --rate 1 \
    --count 10 \
    --value-generation manual
```


### Arguments
| Argument             | Description                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------- |
| `--mode`             | Transport mode: `http` or `mqtt`.                                                             |
| `--device`           | Device `serial_id` to simulate. Must exist in DB.                                             |
| `--rate`             | Messages per second (1 by default).                                                           |
| `--count`            | Number of messages to send.                                                                   |
| `--value-generation` | `manual` – user inputs values for each metric; `random` – interactive random values; `non-interactive` – headless random defaults for smoke/CI. |
| `--http-url`         | URL for HTTP mode (default: `http://localhost:8000/api/telemetry/`).                          |
| `--mqtt-broker`      | Hostname of MQTT broker (default: `localhost`).                                               |
| `--mqtt-topic`       | Topic for MQTT messages (default: `telemetry`).                                               |
| `--schema-version`   | Version of the telemetry schema (default: `1`).                                               |

> Tip: If you’re running outside Docker, ensure the API URL and broker host are reachable from your machine.

### Valid Device Serial IDs
| Serial ID         | Name                         | Description                                              |
| ----------------- | ---------------------------- | -------------------------------------------------------- |
| SN-A1-TEMP-0001   | Living Room Thermometer      | Indoor temperature + humidity sensor in living room      |
| SN-A1-HUM-0002    | Basement Humidity Sensor     | Humidity sensor monitoring basement moisture level       |
| SN-A1-PRES-0003   | Outdoor Pressure Sensor      | Atmospheric pressure sensor mounted outside the building |
| SN-A1-MOTION-0004 | Garage Motion Detector       | Motion detection sensor for garage security              |
| SN-A1-STATUS-0005 | Main Gateway Status Monitor  | Reports gateway uptime and connectivity status           |
| SN-B2-TEMP-0101   | Office Climate Sensor        | Temperature and humidity in office workspace             |
| SN-B2-FW-0103     | Edge Device Firmware Monitor | Reports firmware version and device status               |

---
## Manual vs Random Modes

Use `--value-generation manual` when you want full control over each message. The simulator prompts for every metric on every send cycle, so you can change values between messages (for example, to test threshold rules or alerting behavior).

Use `--value-generation random` to generate values automatically. The first time you run random mode for a device, the simulator asks you to configure:

- Numeric metrics: `min` and `max` bounds used for random values.
- String metrics: a comma-separated list of allowed values (the simulator picks from these).
- Boolean metrics: random `true`/`false` values.

Those settings apply for the rest of the run and across all messages in that session. If you need different ranges or enums, re-run the simulator and reconfigure the prompts.

Use `--value-generation non-interactive` to skip all prompts and use safe defaults for random values. This mode is intended for smoke tests and CI pipelines.

---
## Payload Structure
The simulator sends JSON payloads in the following format:
```json
{
  "schema_version": 1,
  "device": "device-01",
  "ts": "2026-01-27T12:00:00Z",
  "metrics": {
      "temperature": 23.5,
      "humidity": 42,
      ...
  }
}
```

> [!IMPORTANT]
> Metric types are inferred from the DB (`numeric`, `bool`, `str`) and must match the device configuration.

---

## Example Prompts
Random mode asks for ranges and enums:
```text
Configuring temperature
temperature, data type numeric | min: 0
temperature, data type numeric | max: 10

Configuring status
status values, data type str | (comma-separated: ok, alert, ...): ok, alert, warning
```

Manual mode asks for a value per metric:
```text
Enter value for temperature, data type numeric: 25
Enter value for humidity, data type numeric: 50
Enter value for status, data type str: active
```