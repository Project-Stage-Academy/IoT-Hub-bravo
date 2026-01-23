# Security Guidelines — MVP

This document outlines the **initial security measures** for the IoT-Catalog-Hub MVP.

---

## 1. Secrets Management

* **Environment Variables:** All sensitive values (e.g., `SECRET_KEY`, DB credentials) are stored in `.env` files.
* **Do not commit `.env` to Git.** Use `.env.example` for reference.
* **CI/CD Pipelines:** Secrets are injected through GitHub Actions / GitLab CI environment variables.

---

## 2. Authentication & Authorization

* **JWT** is used for API authentication.
* **Django Admin:** Separate superuser credentials; role-based access (Admin / Client).
* **Access Control:** Ensure only authorized users can access device data and rule management endpoints.

---

## 3. Transport Security (TLS)

* **External endpoints:** TLS should be enabled in staging/production environments.
* **Development:** TLS is optional; local dev uses HTTP.
* **Certificates:** Use self-signed certs for staging, production requires valid CA-issued certificates.

---

## 4. Database Security

* Database passwords stored in `.env` or CI secrets.
* Local PostgreSQL / TimescaleDB runs in Docker with isolated network.
* Avoid exposing DB ports publicly in production.

---

## 5. Messaging Security

* Kafka / RabbitMQ connections can be secured using SSL/TLS in production.
* Authentication between services is recommended when moving to microservices.

---

## 6. Minimal Security Practices

* Do not reuse development secrets in production.
* Rotate keys regularly.
* Review access permissions for Admin and Client users periodically.
* Keep dependencies up-to-date to avoid known vulnerabilities.