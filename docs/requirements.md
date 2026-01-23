# IoT Catalog Hub — Requirements (MVP)

## 1. Scope of the MVP

### 1.1 In Scope (MVP)

The MVP focuses on validating the core end-to-end flows of an IoT platform implemented as a **monolithic application**, with supporting services running in the same development stack.

The MVP **must include**:

* Device registration and management
* Telemetry ingestion via HTTP or MQTT
* Persistent storage of device metadata and telemetry data
* Definition and execution of simple trigger-based rules
* Message routing to internal consumers (alerts, downstream services)
* Administrative interface for managing devices, rules, and users
* Observability for core system components (metrics and basic dashboards)
* Local development and staging deployment via Docker Compose
* CI pipelines for build, test, and packaging validation

### 1.2 Out of Scope (MVP)

The following items are **explicitly excluded** from the MVP:

* Full microservices deployment in production
* Horizontal autoscaling and advanced orchestration (e.g. Kubernetes)
* Advanced rule authoring (e.g. visual rule builders or complex DSLs)
* Long-term cold storage and tiered archival strategies
* Multi-region deployment and disaster recovery
* SLA-backed availability guarantees
* End-user dashboards for analytics (beyond admin and basic inspection)
* Fine-grained multi-tenant isolation

---

## 2. Functional Requirements

### 2.1 API and Core Platform

* The system SHALL expose a RESTful HTTP API for:

  * Device registration, update, and deactivation
  * Telemetry ingestion (HTTP-based)
  * Rule definition and management
  * Querying stored telemetry data (bounded by time range)
* The API SHALL be implemented using Django as an API Gateway and Admin UI.
* The system SHALL provide OpenAPI (Swagger) specifications for all public APIs.
* The system SHALL support versioned APIs

### 2.2 Authentication and Authorization

* The system SHALL support JWT-based authentication for API access.
* The system SHALL define at least two roles:

  * **Admin**: full access to device, rule, and system configuration
  * **Client**: access limited to assigned devices and telemetry
* The Django Admin interface SHALL be protected by authentication.
* Secrets and credentials SHALL NOT be hardcoded and MUST be provided via environment variables.

### 2.3 Device Registry

* The system SHALL allow registering IoT devices with unique identifiers.
* Each device SHALL have associated serial number.
* Devices MAY be activated or deactivated without deleting historical data.

### 2.4 Telemetry Ingestion

* The system SHALL accept telemetry data via:

  * HTTP endpoints or MQTT ingestion agents
* Telemetry messages SHALL include:

  * Device identifier
  * Timestamp
  * Metric name(s) and value(s)
* Telemetry data SHALL be persisted in PostgreSQL or TimescaleDB.
* The system SHALL validate telemetry payloads before storage.

### 2.5 Rules and Event Processing

* The system SHALL support simple rule definitions based on telemetry thresholds or conditions.
* Rules SHALL be evaluated by a dedicated rule evaluation component.
* When a rule is triggered, the system SHALL emit an event to the messaging broker.
* Rule execution results SHALL be observable via logs and metrics.

### 2.6 Messaging and Streaming

* The system SHALL use Kafka or RabbitMQ as a message broker.
* Telemetry and rule events SHALL be published to the broker for downstream consumers.
* A streaming/aggregation component SHALL process telemetry streams for basic aggregations.

### 2.7 Background Jobs

* The system SHALL support background processing for:

  * Rule evaluation
  * Telemetry aggregation
  * Notifications or internal message dispatch
* Background jobs SHALL be observable and restartable in development.

---

## 3. Non-Functional Requirements

### 3.1 Performance

* The system SHALL support at least **100 registered devices** in the MVP.
* The system SHALL ingest at least **50 telemetry messages per second** in a local or staging environment.
* API endpoints for telemetry ingestion SHALL respond within **< 200 ms** under nominal load.
* Rule evaluation latency SHALL be **< 1 second** from telemetry ingestion to event emission.

### 3.2 Availability

* The MVP SHALL target **≥ 99% uptime** in local and staging environments, excluding planned maintenance.
* Core services (API, database, broker) SHALL fail fast and expose healthcheck endpoints.
* The system SHALL be restartable without manual intervention using Docker Compose.

### 3.3 Data Retention

* Telemetry data SHALL be retained for a configurable period.
* Device metadata and rule definitions SHALL be retained indefinitely unless explicitly deleted.
* Retention policies SHALL be configurable via environment variables or configuration files.

### 3.4 Observability

* The system SHALL expose Prometheus-compatible metrics.
* Metrics SHALL include:

  * API request counts and latencies
  * Telemetry ingestion rates
  * Rule execution counts and failures
* Grafana dashboards SHALL be provided for basic system monitoring.
* Logs SHALL be accessible via Docker Compose logging.

---

## 4. Acceptance Criteria (Monolith MVP Milestone)

The monolithic MVP is considered complete when:

* A developer can clone the repository and start the full stack using Docker Compose without manual intervention.
* Devices can be registered via API or admin UI and persist correctly in the database.
* Telemetry can be ingested via HTTP and MQTT and is stored in the database.
* At least one rule can be defined, evaluated, and triggered based on incoming telemetry.
* Triggered rules result in messages published to the messaging broker.
* Basic telemetry aggregation is performed by the streaming component.
* JWT authentication is enforced for protected API endpoints.
* Prometheus successfully scrapes metrics from core components.
* All services expose healthcheck endpoints and restart cleanly.
* CI pipelines complete successfully for build, test, and packaging stages.
* Documentation exists for setup, architecture, and basic operations.
