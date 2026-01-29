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

| Field         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `timestamp`   | Log creation time (UTC)                                     |
| `level`       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `logger_name` | Name of the logger that produced the log                    |
| `message`     | Human-readable log message                                  |
| `request_id`  | Unique ID for a request (if available)                      |
| `duration`    | Request execution time in milliseconds (if available)       |
| `status_code` | status code (for request logs)                              |

Additional fields may appear depending on context (e.g. Celery task info or custom application fields).

## Request Context

Forrequests, context is provided via:

* **Middleware** – stores request-scoped data (request ID, duration time) using `contextvars`
* **Logging filter** – injects request context into every log record

This ensures that all logs generated during a request share the same `request_id` and timing data.

## Django Logs

* Django framework logs use the `django` logger namespace
* The `django` logger is explicitly declared to ensure its logs use the same handlers and JSON format as application logs

## Celery Logs (TEMPORARY)

* Celery workers use the same logging configuration
* Task logs automatically include:

  * task name
  * task ID
  * log level and message

Because logs are written to stdout in JSON, no additional Celery-specific log files are required in containers.

## Querying Logs (TEMPORARY)

`docker logs web -n 5 2>&1 | jq ".level"` - only bash

### By request ID

Use `request_id` to trace a single request across multiple log entries:

```text
request_id=\"c25d9547-c08f-4248-81a3-240ce5a83993\"
```

### By logger

```text
logger_name=django.request
```

```text
logger_name=rules
```

### By level

```text
level=ERROR
```

### Slow requests

```text
duration > 500
```

## Why JSON + stdout

* Container-friendly (Docker / Kubernetes best practice)
* Easy to parse and query
* No shared filesystem or log rotation required
* Works seamlessly with centralized logging systems

## Local Development (TEMPORARY / MUST CHANGE)

When running locally, logs are still emitted as JSON to stdout. You can:

* Pipe output to `jq` for readability
* Redirect logs to a file if needed

Example:

```bash
python manage.py runserver | jq
```
