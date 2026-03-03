# Exporting Events

## Overview

This document explains how to use the `export_events` Django management command to export events to CSV. The command is implemented in `backend/apps/rules/management/commands/export_events.py` and writes a CSV with one row per `Event`.

See the command source: [backend/apps/rules/management/commands/export_events.py](backend/apps/rules/management/commands/export_events.py#L1-L200)

## Prerequisites

- A working development environment for the project (Docker Compose recommended).
- Database and web container available (or run locally with the project's Python environment).
- Write permission to the target output folder (default: `exports/`).

## What the command does

- Exports events ordered by `timestamp` (newest first).
- Default output file: `exports/events_export.csv` (created under repository root if not provided).
- Accepts `--since` to filter events created on/after an ISO timestamp.
- Accepts `--output` to set a custom output path.
- Prints a success message with the number of exported events.

CSV header fields produced:
- `id`
- `timestamp` (Django timezone-aware datetime)
- `rule` (the rule name)
- `acknowledged` (true/false)
- `trigger_telemetry_id` (nullable)
- `trigger_device_id` (nullable)

## Usage examples

Run locally (from repo root) with your Python environment:

```bash
python backend/manage.py export_events
```

Filter by ISO timestamp (UTC or timezone-aware string):

```bash
python backend/manage.py export_events --since "2026-02-01T00:00:00Z"
```

Write to a custom output path:

```bash
python backend/manage.py export_events --output /tmp/my_events.csv
```

Using Docker Compose (recommended development flow):

```bash
docker compose exec web python manage.py export_events
# or with --since and output
docker compose exec web python manage.py export_events --since "2026-02-01T00:00:00Z" --output /tmp/events.csv
```

If you want the exported file on your host and you used the container example with `/tmp/events.csv`, copy it out with `docker cp` or mount a host directory to the container.

## Common scenarios

- Export recent events only (last 24h):

```bash
python backend/manage.py export_events --since "$(date -Iseconds -d '24 hours ago')"
```

- Append scheduled daily export (example cron entry) — put this on the host where the repo and `docker` are available:

```cron
# run daily at 2:00, write to repo exports dir
0 2 * * * cd /path/to/IoT-Hub-bravo && docker compose exec -T web python manage.py export_events --output exports/events_$(date +\%F).csv >> exports/export_events.log 2>&1
```

Note: When using cron, prefer absolute paths and test the command manually before scheduling.

## Troubleshooting

- Invalid `--since` value: the command validates `--since` using Django's `parse_datetime`. If invalid, it prints an error and exits without writing a file. Use ISO format (e.g. `2026-02-01T12:34:56Z`).

- Output file not writable: ensure the directory exists and the process has write permission. The command will create `exports/` under the project root if no `--output` is specified.

- No events exported: check the database and the `timestamp` filter; try running the command without `--since` to confirm events exist.

- Running on CI: ensure the CI runner has access to the Django settings and the database or use a test database seeded with events.

## Notes about timezones

- The command uses Django `DateTimeField` values. When filtering with `--since`, pass timezone-aware ISO datetimes to avoid ambiguity.
- The CSV `timestamp` values are Django datetimes and may be timezone-aware depending on your `TIME_ZONE` and `USE_TZ` settings.

## Automation ideas

- Add a scheduled job (cron, systemd timer, or CI pipeline) to regularly export events.
- Use the `--since` flag to only export incremental data and avoid rewriting large files.
- Post-process CSVs (compress, upload to S3) in subsequent steps.

## Security and data handling

- Ensure exported CSVs are stored securely if they contain sensitive information.
- Rotate or delete old export files if they contain PII.

## Where the file ends up by default

- Default path: `exports/events_export.csv` in the repository root. The `exports/` folder is created automatically by the command if it doesn't exist.

## Example run and output

```bash
$ python backend/manage.py export_events --since "2026-02-01T00:00:00Z"
Exported 42 events to /full/path/to/repo/exports/events_export.csv
```

That's it — if you want, I can:

- Commit this file and open a PR, or
- Add a short entry in `docs/README` referencing this doc.
