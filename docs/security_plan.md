# Security Plan for IoT Hub MVP

## Overview

This document outlines the security goals, threat model, and protection scope for the IoT Hub monolithic MVP. It defines the security baseline for development and staging environments, ensuring consistent security practices across the team.

## Security Goals

### Primary Objectives

1. **Confidentiality**: Protect sensitive data (user credentials, device secrets, telemetry data) from unauthorized access
2. **Integrity**: Ensure data and API communications cannot be tampered with
3. **Availability**: Protect against denial-of-service attacks that could disrupt device telemetry ingestion
4. **Authentication & Authorization**: Enforce proper access control for API endpoints and admin interfaces
5. **Secrets Management**: Safely handle secrets (database passwords, JWT keys, API tokens) without committing them to version control

### MVP Scope

For the MVP phase, we focus on:
- Establishing secure development practices
- Protecting local development environments
- Setting up authentication/authorization foundations
- Preparing for staging deployment security

## Threat Model

### Assumptions

**Trust Boundaries:**
- Local development: Developers' machines are trusted, but network traffic may be intercepted
- Staging: External network is untrusted; internal services communicate over Docker networks
- Database: TimescaleDB is accessible only within Docker network, not exposed to host

**Attack Surfaces:**
1. **API Endpoints** (`/api/*`): Exposed to clients (web frontend, IoT devices)
2. **Admin Interface** (`/admin/`): Accessible to authenticated admin users
3. **Database**: TimescaleDB exposed on port 5432 (dev only, should be restricted in staging)
4. **Development Environment**: Docker containers, local file system

### Threat Categories

#### 1. Unauthorized Access
- **Threat**: Attackers gain access to API without valid credentials
- **Impact**: Data exfiltration, unauthorized device registration, telemetry manipulation
- **Mitigation**: JWT-based authentication, role-based access control (RBAC)

#### 2. Man-in-the-Middle (MITM) Attacks
- **Threat**: Interception of HTTP traffic in local dev or staging
- **Impact**: Credential theft, session hijacking, data tampering
- **Mitigation**: TLS encryption for all HTTP traffic (HTTPS in dev/staging)

#### 3. Credential Compromise
- **Threat**: Leaked secrets (database passwords, SECRET_KEY) in code or logs
- **Impact**: Full system compromise, data breach
- **Mitigation**: Secrets stored in `.env` (gitignored), CI secrets management, no hardcoded credentials

#### 4. Denial of Service (DoS)
- **Threat**: Excessive API requests overwhelming the server
- **Impact**: Service unavailability, device telemetry ingestion failure
- **Mitigation**: Rate limiting middleware, network-level protections, monitoring, and scaling

#### 5. Injection Attacks
- **Threat**: SQL injection, command injection via API inputs
- **Impact**: Database compromise, remote code execution
- **Mitigation**: Django ORM (parameterized queries), input validation

#### 6. Dependency Vulnerabilities
- **Threat**: Known vulnerabilities in Python packages or Docker base images
- **Impact**: Exploitation of vulnerable dependencies
- **Mitigation**: Regular dependency scanning (safety, dependabot), timely updates

## Scope of Protections

### Development Environment

**Applied Protections:**
- ✅ TLS termination via nginx dev proxy (HTTPS on localhost)
- ✅ Secrets stored in `.env` file (gitignored)
- ✅ JWT authentication for API endpoints
- ✅ Rate limiting middleware for API endpoints
- ✅ Dependency vulnerability scanning in CI
- ✅ Database access restricted to Docker network

**Not Applied (Acceptable for Dev):**
- ❌ Production-grade certificate validation (self-signed certs acceptable)
- ❌ WAF (Web Application Firewall)
- ❌ Advanced intrusion detection
- ❌ Full audit logging

**Security Notes:**
- Dev certificates are trusted locally only (mkcert)
- `DEBUG=True` is acceptable in dev (shows error details)
- Database port may be exposed to host for debugging (should be restricted in staging)

### Staging Environment

**Applied Protections:**
- ✅ TLS with valid certificates (Let's Encrypt or internal CA)
- ✅ Secrets from secure secret store (CI/CD secrets, not `.env` files)
- ✅ JWT authentication with proper token expiration
- ✅ Rate limiting middleware with stricter limits
- ✅ `DEBUG=False` (no error details exposed)
- ✅ Database access restricted to application network only
- ✅ Dependency vulnerability scanning in CI/CD pipeline
- ✅ Security headers (HSTS, CSP, X-Frame-Options)

**Additional Considerations:**
- Network ACLs restricting access to staging services
- Basic authentication for internal APT repository
- Regular security updates for base images and dependencies

### Production (Future)

**Out of Scope for MVP:**
- Production security hardening will be defined in a separate security plan
- Includes: WAF, DDoS protection, advanced monitoring, compliance requirements

## Security Controls Summary

| Control | Dev | Staging | Notes |
|---------|-----|---------|-------|
| TLS/HTTPS | ✅ (self-signed) | ✅ (valid cert) | Required for all environments |
| JWT Auth | ✅ | ✅ | Token lifetime: 60 min (dev), 15 min (staging) |
| Rate Limiting | ✅ | ✅ | Configurable per endpoint (see settings) |
| Secrets Management | `.env` (gitignored) | CI secrets | Never commit secrets |
| Dependency Scanning | ✅ (CI) | ✅ (CI) | Automated in pipeline |
| Database Access | Docker network | Restricted network | No public exposure |
| Debug Mode | ✅ (allowed) | ❌ (disabled) | Security risk if enabled in staging |

## Compliance & Best Practices

### Development Team Responsibilities

1. **Never commit secrets**: Use `.env` for local dev, CI secrets for CI/CD
2. **Rotate compromised secrets**: Follow `docs/security_checklist.md` procedures
3. **Review dependency updates**: Triage vulnerability scan findings promptly
4. **Follow authentication patterns**: Use JWT tokens as documented in `docs/auth.md`
5. **Test security controls**: Validate TLS, secrets, and auth before demos

### Incident Response

If a security incident occurs (compromised secret, exposed credential, etc.):

1. **Immediately**: Rotate the compromised secret (see `docs/security_checklist.md`)
2. **Assess**: Determine scope of exposure (dev, staging, or production)
3. **Document**: Record incident in security log
4. **Remediate**: Apply fixes and update security controls if needed

## Rate Limiting

Rate limiting is implemented via Django middleware to protect against DoS attacks and abuse. The middleware tracks requests per IP address and endpoint pattern.

### Default Limits

| Endpoint Pattern | Limit | Window | Purpose |
|-----------------|-------|--------|---------|
| `/api/telemetry/` | 1000 requests | 60 seconds | Device ingestion endpoints (high volume expected) |
| `/admin/` | 30 requests | 60 seconds | Admin interface (lower volume, sensitive operations) |
| `/api/auth/login` | 5 requests | 60 seconds | Login endpoint (prevent brute force) |

### Configuration

Rate limiting can be toggled and configured via Django settings:

```python
RATE_LIMIT_ENABLED = True  # Set to False to disable

RATE_LIMIT_CONFIG = {
    '/api/telemetry/': {
        'limit': 1000,  # requests
        'window': 60,   # seconds
    },
    '/admin/': {
        'limit': 30,
        'window': 60,
    },
    '/api/auth/login': {
        'limit': 5,
        'window': 60,
    },
}
```

### Environment Variables

Override defaults via `.env`:

```env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_TELEMETRY_LIMIT=1000
RATE_LIMIT_TELEMETRY_WINDOW=60
RATE_LIMIT_ADMIN_LIMIT=30
RATE_LIMIT_ADMIN_WINDOW=60
RATE_LIMIT_LOGIN_LIMIT=5
RATE_LIMIT_LOGIN_WINDOW=60
```

### Response Format

When rate limit is exceeded, the middleware returns:

```json
{
    "code": 429,
    "message": "Rate limit exceeded",
    "retry_after": 60
}
```

HTTP Status: `429 Too Many Requests`  
Header: `Retry-After: 60`

### Implementation Details

- Uses Django's cache framework (LocMemCache by default)
- Tracks requests per IP address and HTTP method
- Sliding window based on cache TTL
- Pattern matching supports prefix matching (trailing `/`)

### Recommendations

**Development:**
- Default limits are permissive to allow testing
- Can be disabled via `RATE_LIMIT_ENABLED=False` if needed

**Staging/Production:**
- Adjust limits based on expected traffic patterns
- Consider using Redis cache backend for distributed rate limiting
- Monitor rate limit hits to detect abuse patterns
- For high-volume telemetry ingestion, consider per-device rate limiting

## References

- [Authentication Plan](./auth.md) - JWT implementation details
- [Security Checklist](./security_checklist.md) - Pre-demo checks and incident response
- [CI/CD Security](./ci.md) - Secrets management in CI
- [Development Environment](./dev-environment.md) - Local setup with TLS

## Document Maintenance

This security plan should be reviewed and updated when:
- New threat vectors are identified
- Security controls are added or modified
- Moving from MVP to production deployment
- Security incidents reveal gaps

**Last Updated**: 2026-01-22
**Next Review**: 2026-04-22

