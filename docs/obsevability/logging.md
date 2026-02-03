# Logging

This document describes how logging is configured in the project, what fields are included in logs, and how to work with them in a container environment.

## Overview

* Django and Celery emit **structured JSON logs by default** when running in containers.
* Logs are written to **stdout** (no file paths required), so they can be collected by Docker or any log aggregation system.

## Log Format

Logs are formatted as JSON objects. A typical log entry looks like:

```json
{
  "timestamp": "2026-01-29 15:19:52,600",
  "level": "WARNING",
  "logger_name": "django.request",
  "message": "Not Found: /",
  "request_id": "c25d9547-c08f-4248-81a3-240ce5a83993",
  "duration": 1.45,
  "status_code": 404
}
```

## Standard Log Fields
### Django
| Field         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `timestamp`   | Log creation time (UTC)                                     |
| `level`       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `logger_name` | Name of the logger that produced the log                    |
| `message`     | Human-readable log message                                  |
| `request_id`  | Unique ID for a request                                     |
| `duration`    | Request execution time in milliseconds                      |

### Celery
| Field         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `timestamp`   | Log creation time (UTC)                                     |
| `level`       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `logger_name` | Name of the logger that produced the log                    |
| `message`     | Human-readable log message                                  |
| `task_id`     | Unique ID for a task (if available)                         |
| `task_name`   | Name of the task (if available)                             |

> **Note:** Additional fields may appear depending on context.

## Request Context

For requests, context is provided via:

* **Middleware** – stores request-scoped data (request ID, duration time) using `contextvars`
* **Logging filter** – injects request context into every log record

This ensures that all logs generated during a request share the same `request_id` and timing data.

## Querying Logs (Bash)

Use `-n N` to adjust the number of log lines returned by Docker.

* Get the log level of the last 5 log entries:

```bash
docker logs web -n 5 2>&1 | jq -R 'fromjson? | .level'
```

* Filter only WARNING logs from the last 10 entries:

```bash
docker logs web -n 10 2>&1 | jq -R 'fromjson? | select(.level == "WARNING")'
```

* Extract only the message field from WARNING logs of the last 15 entries:

```bash
docker logs web -n 15 2>&1 | jq -R 'fromjson? | select(.level == "WARNING") | .message'
```
