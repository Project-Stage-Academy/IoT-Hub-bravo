# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in this project, please report it
responsibly:

**Email:** iot-hub-bravo@projecstage.academy

Do **not** open a public GitHub issue for security vulnerabilities.

---

## Secrets Management

- **Environment Variables:** All sensitive values (e.g., `SECRET_KEY`, DB credentials) are stored in `.env` files.
- **Do not commit `.env` to Git.** Use `.env.example` for reference.
- **.gitignore:** Ensure `.env` and `*.env` are listed. See [.gitignore](../.gitignore).
- **CI/CD Pipelines:** Secrets are injected through GitHub Actions environment variables.

---

## Authentication & Authorization

- **JWT** is used for API authentication.
- **Django Admin:** Separate superuser credentials; role-based access (Admin / Operator / Viewer).
- **Access Control:** Only authorized users can access device data and rule management endpoints.

---

## Transport Security (TLS)

- **Production:** TLS must be enabled for all external endpoints.
- **Staging:** Use self-signed certificates.
- **Development:** TLS is optional; local dev uses HTTP.
  Do not use production secrets in local/dev environments without TLS.

---

## Database Security

- Database passwords stored in `.env` or CI secrets.
- Local PostgreSQL / TimescaleDB runs in Docker with isolated network.
- Avoid exposing DB ports publicly in production.

---

## Messaging Security

- Redis / RabbitMQ connections can be secured using SSL/TLS in production.
- Authentication between services is recommended when moving to microservices.

---

## Dependency Security Alerts

### Dependabot

This repository uses [Dependabot](https://docs.github.com/en/code-security/dependabot)
to monitor dependencies for known vulnerabilities.

- **Configuration:** [.github/dependabot.yml](../.github/dependabot.yml)
- **Schedule:** Monthly checks for Python and GitHub Actions dependencies
- **Alerts:** Visible in **Security > Dependabot alerts** tab on GitHub

### Triage Process

| Step | Action | Owner | SLA |
|------|--------|-------|-----|
| 1 | Dependabot creates alert or PR | Automated | — |
| 2 | Review alert severity | DevOps Lead / Backend Lead | 2 business days |
| 3 | Assess impact on project | Backend Lead | 3 business days |
| 4 | Merge fix or dismiss with reason | Backend Lead | 5 business days (critical: 1 day) |

### Severity Response Times

| Severity | Response SLA | Fix SLA |
|----------|-------------|---------|
| **Critical** | Same day | 1 business day |
| **High** | 1 business day | 3 business days |
| **Medium** | 3 business days | 5 business days |
| **Low** | 5 business days | Next sprint |

### How to Check Alerts

1. Go to **Security > Dependabot alerts** in the GitHub repository
2. Review open alerts sorted by severity
3. Click on an alert for details and recommended fix
4. Either merge the Dependabot PR or manually update the dependency

### Dismissing Alerts

If an alert is not applicable, dismiss it with a reason:

- **Not applicable** — the vulnerable code path is not used
- **Risk accepted** — the team has reviewed and accepted the risk
- **False positive** — the alert does not apply to our usage

Always leave a comment explaining the dismissal reason.

---

## CI Security Checks

- **Linting:** `ruff` and `black` run on every PR
- **Tests:** `pytest` runs on every PR against a real database
- **Build:** Docker image build is verified on every PR

---

## Best Practices

- Never commit secrets, passwords, or API keys
- Use environment variables for sensitive configuration
- Keep dependencies up to date
- Review Dependabot PRs promptly
- Use `.env` files locally (excluded via `.gitignore`)
- Do not reuse development secrets in production
- Rotate keys regularly
- Review access permissions for Admin and Client users periodically
