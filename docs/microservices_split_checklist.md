# MVP-to-Microservices Split Checklist

This checklist ensures the IoT-Catalog-Hub monolith is ready to be split into separate services.

---

## 1. API Contract Readiness

* [ ] REST endpoints are well-documented in OpenAPI / Swagger
* [ ] All endpoints return consistent responses with proper status codes
* [ ] Authentication (JWT) and authorization are applied consistently
* [ ] Versioning strategy defined for APIs

---

## 2. Database Ownership & Schema

* [ ] Tables and models are clearly mapped to future services
* [ ] Time-series telemetry data can be partitioned if needed
* [ ] Migrations are applied and stable
* [ ] Backup & restore procedures verified

---

## 3. Service Boundaries Defined

* [ ] Clear separation of responsibilities:

  * Auth & API Gateway
  * Device Registry
  * Telemetry Ingestor
  * Rule Engine
  * Stream Aggregator / Processor
  * Worker / Notification service
* [ ] Minimal inter-service coupling for future extraction

---

## 4. CI/CD Pipelines

* [ ] Pipelines can build individual service images (.deb / Docker)
* [ ] Unit and integration tests pass consistently
* [ ] Deployments reproducible for each service

---

## 5. Observability & Logging

* [ ] Prometheus metrics collected per component
* [ ] Grafana dashboards reflect component-level metrics
* [ ] Logs structured and easily filtered per service

---

## 6. Data Migration & Event Handling

* [ ] Telemetry ingestion flow validated end-to-end
* [ ] Rule evaluation emits events reliably
* [ ] Event routing via Kafka / RabbitMQ confirmed
* [ ] Historical data accessible post-split

---

## 7. Security & Access Control

* [ ] Secrets handled securely in Compose & CI
* [ ] TLS enforced for external endpoints
* [ ] Role-based access control validated

---

## 8. Validation & Documentation

* [ ] Developer onboarding runbook tested from fresh environment
* [ ] Operations runbook commands verified
* [ ] Troubleshooting guide covers known failure scenarios
* [ ] Architecture diagrams updated to reflect monolith boundaries

---

## 9. Go/No-Go Decision

* [ ] All above criteria satisfied
* [ ] Monolith stable in staging environment
* [ ] Team agrees readiness for microservices extraction

> Once all items are checked, the monolith can safely be split into microservices following defined boundaries.