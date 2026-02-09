# API Change Process

This document describes how to manage changes to the API, especially breaking changes.

## Breaking changes, versioning, and deprecation

### What counts as a breaking change

A breaking change is any modification that breaks existing clients. Examples:

1. Removing a required field or an entire endpoint.
2. Changing a field type (e.g., `integer` to `string`).
3. Removing an enum value or restricting validation rules.
4. Changing response structure or adding required fields to responses.
5. Changing HTTP method semantics or status codes.
6. Moving or renaming fields in request/response bodies.

### Versioning requirement

**All breaking changes require versioning**. Choose one or both:

- Bump the OpenAPI spec version in `docs/api.yaml` (e.g., `1.0.0` → `2.0.0`).
- Introduce a new versioned API endpoint (e.g., `/v2/devices/` alongside `/v1/devices/`).

Update the `info.version` field in `docs/api.yaml`:

```yaml
openapi: 3.0.3
info:
  title: IoT Hub API
  version: "2.0.0"  # Bumped from 1.0.0
```

### Stakeholder notification

Before merging a breaking change:

1. **Notify relevant teams**: frontend, QA, mobile, and external API consumers (if applicable).
2. **Provide timeline**: include planned removal date or deprecation period (minimum 1 sprint).
3. **Document migration path**: explain how clients should adapt.
4. **Update PR description**: link this file and reference the versioning approach.

### Deprecating fields in the spec

Mark deprecated fields in `docs/api.yaml` using `deprecated: true`:

```yaml
components:
  schemas:
    Device:
      type: object
      properties:
        id:
          type: integer
        legacy_name:
          type: string
          deprecated: true
          description: "Deprecated since v1.5.0. Use `name` field instead. Planned removal: v2.0.0 (2026-03-01)."
        name:
          type: string
```

Also mark deprecated endpoints:

```yaml
paths:
  /v1/devices/{id}:
    get:
      deprecated: true
      summary: "Deprecated. Use GET /v2/devices/{id} instead. Planned removal: v2.0.0 (2026-03-01)."
      operationId: get_device_v1
```

Linting and contract tests will flag deprecated fields, alerting developers before merge.
