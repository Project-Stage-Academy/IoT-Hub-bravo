# IoT Telemetry Simulator

The IoT Telemetry Simulator allows you to generate and send simulated telemetry data for development and testing purposes. It supports both HTTP and MQTT transport modes and can operate in manual or random value generation modes.

---

## Table of Contents

- [Requirements](#requirements)

- [Running the Simulator](#running-the-simulator)

- [Payload Structure](#payload-structure)

- [Example Payload Templates](#example-payload-templates)


---

## Requirements

- Access to your development web container and database (for fetching devices & metrics)

- Docker Compose running web, db, and optionally mosquitto for MQTT

---

## Running the Simulator
```bash
# HTTP mode, random values, device SN-A1-TEMP-0001, 10 messages, 1 message per second
docker compose exec web python simulator/run.py \
    --mode http \
    --device SN-A1-TEMP-0001 \
    --rate 1 \
    --count 10 \
    --value-generation random

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
| `--value-generation` | `manual` – user inputs values for each metric; `random` – random values generated per metric. |
| `--http-url`         | URL for HTTP mode (default: `http://localhost:8000/api/telemetry/`).                          |
| `--mqtt-broker`      | Hostname of MQTT broker (default: `localhost`).                                               |
| `--mqtt-topic`       | Topic for MQTT messages (default: `telemetry`).                                               |
| `--schema-version`   | Version of the telemetry schema (default: `1`).                                               |

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
## Payload Structure
The simulator sends JSON payloads in the following format:
``` bash
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

 [!IMPORTANT] Note: Metric types are inferred from the DB (numeric, bool, str) and must match what is configured for the device.

---

## Example Payload Templates
Random mode prompts the dev to input numeric ranges and string enums:
```bash
Configuring temperature
temperature min: 0
temperature max: 10

Configuring status
status values (comma-separated): ok, alert, worning 
```

Manual mode prompts the dev to input a value for each metric:
```bash
Enter value for temperature (numeric): 25
Enter value for humidity (numeric): 50
Enter value for status (str): active

```