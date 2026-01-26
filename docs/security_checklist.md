# Security Checklist

This document provides pre-demo security checks, procedures for rotating compromised secrets, token revocation, and minimal incident response steps.

## Pre-Demo Security Checks

Complete these checks before any demo or presentation (target: **15 minutes**).

### ✅ TLS/HTTPS Validation

- [ ] **Certificates exist and are valid**
  ```bash
  ls -la certs/localhost.pem certs/localhost-key.pem
  ```

- [ ] **HTTPS works without browser warnings**
  - Open `https://localhost` in browser
  - Verify no certificate errors (if using mkcert)
  - Verify HTTP redirects to HTTPS

- [ ] **nginx container is running**
  ```bash
  docker compose ps nginx
  ```

### ✅ Secrets Configuration

- [ ] **`.env` file exists and contains all required variables**
  ```bash
  test -f .env && echo "✓ .env exists"
  ```

- [ ] **All [SECRET] variables are set (not placeholder values)**
  - `SECRET_KEY` - not "django-insecure-change-this..."
  - `DB_PASSWORD` - not "iot_password"
  - `JWT_SECRET_KEY` - not "your-jwt-secret-key-here..."

- [ ] **`.env` is in `.gitignore` and not committed**
  ```bash
  git check-ignore .env && echo "✓ .env is ignored"
  ```

### ✅ JWT Authentication

- [ ] **Can obtain JWT token via login endpoint**
  ```bash
  curl -X POST https://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"testpass"}' \
    -k
  ```
  Expected: `200 OK` with `access_token` in response

- [ ] **Token can be used to access protected endpoint**
  ```bash
  curl -X GET https://localhost/api/devices/ \
    -H "Authorization: Bearer <token>" \
    -k
  ```
  Expected: `200 OK` (not `401 Unauthorized`)

### ✅ Rate Limiting

- [ ] **Rate limiting is enabled**
  - Check `RATE_LIMIT_ENABLED=True` in `.env`

- [ ] **Rate limit triggers 429 response**
  ```bash
  # Send 6 requests rapidly to /api/auth/login
  for i in {1..6}; do
    curl -X POST https://localhost/api/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username":"test","password":"test"}' \
      -k -w "\nHTTP: %{http_code}\n"
  done
  ```
  Expected: 6th request returns `429 Too Many Requests`

### ✅ APT Repository Access (if applicable)

- [ ] **Repository server is running**
  ```bash
  cd devops/apt-repo && docker compose ps
  ```

- [ ] **Basic auth works**
  ```bash
  curl -u admin:password http://localhost:8080/repo
  ```
  Expected: `200 OK` or directory listing

- [ ] **Unauthenticated access is denied**
  ```bash
  curl http://localhost:8080/repo
  ```
  Expected: `401 Unauthorized`

### Quick Validation Script

Run all checks at once:

```bash
#!/bin/bash
echo "=== TLS Check ==="
test -f certs/localhost.pem && echo "✓ Certificates exist" || echo "✗ Certificates missing"

echo "=== Secrets Check ==="
test -f .env && echo "✓ .env exists" || echo "✗ .env missing"
grep -q "SECRET_KEY=django-insecure" .env && echo "✗ SECRET_KEY not changed" || echo "✓ SECRET_KEY configured"

echo "=== JWT Check ==="
TOKEN=$(curl -s -X POST https://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  -k | jq -r '.access_token')
test -n "$TOKEN" && echo "✓ JWT token obtained" || echo "✗ JWT token failed"

echo "=== Rate Limit Check ==="
RESPONSE=$(curl -s -w "%{http_code}" -X POST https://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' \
  -k -o /dev/null)
echo "Response code: $RESPONSE"
```

## Rotate Compromised Secret

If a secret is compromised (leaked, exposed in logs, committed to git, etc.), follow these steps:

### Step 1: Identify Compromised Secret

Determine which secret was compromised:
- `SECRET_KEY` - Django signing key
- `DB_PASSWORD` - Database password
- `JWT_SECRET_KEY` - JWT signing key
- Other secrets from `.env`

### Step 2: Generate New Secret

**For SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**For JWT_SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**For DB_PASSWORD:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### Step 3: Update Local Development

1. **Stop services:**
   ```bash
   docker compose down
   ```

2. **Update `.env` file:**
   ```bash
   # Edit .env and replace the compromised secret
   nano .env  # or use your preferred editor
   ```

3. **If DB_PASSWORD changed, update database:**
   ```bash
   # Connect to database
   docker compose exec db psql -U postgres
   
   # Change password
   ALTER USER iot_user_db WITH PASSWORD 'new-password';
   \q
   ```

4. **Restart services:**
   ```bash
   docker compose up -d
   ```

### Step 4: Update CI/CD Secrets

**GitHub Actions:**
1. Go to Repository → Settings → Secrets and variables → Actions
2. Find the compromised secret
3. Click "Update" and paste new value
4. Save

**GitLab CI:**
1. Go to Settings → CI/CD → Variables
2. Find the compromised secret
3. Click "Edit" and update value
4. Save

### Step 5: Verify

- [ ] Services start successfully
- [ ] Can authenticate and obtain JWT token
- [ ] Database connections work
- [ ] No errors in logs

### Step 6: Document

Record the rotation in security log:
- Date/time of rotation
- Which secret was rotated
- Reason (compromised, routine rotation, etc.)
- Who performed the rotation

## Revoke Dev Token

To invalidate a JWT token (e.g., if a developer's token is compromised):

### Option 1: Rotate JWT_SECRET_KEY (Invalidates All Tokens)

This is the simplest approach for MVP (no token blacklist):

1. **Generate new JWT_SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update `.env`:**
   ```bash
   JWT_SECRET_KEY=<new-key>
   ```

3. **Restart services:**
   ```bash
   docker compose down
   docker compose up -d
   ```

**Impact:** All existing tokens become invalid. Users must re-authenticate.

### Option 2: Token Blacklist (Future Enhancement)

For production, implement token blacklist using Redis or database:

```python
# Store revoked token IDs in cache/database
BLACKLISTED_TOKENS = set()

def revoke_token(jti):
    BLACKLISTED_TOKENS.add(jti)
    cache.set(f"blacklist:{jti}", True, timeout=TOKEN_LIFETIME)

def is_token_revoked(jti):
    return jti in BLACKLISTED_TOKENS or cache.get(f"blacklist:{jti}")
```

### Verify Token Revocation

```bash
# Try to use old token
curl -X GET https://localhost/api/devices/ \
  -H "Authorization: Bearer <old-token>" \
  -k

# Expected: 401 Unauthorized
```

## Minimal Incident Response

If a security incident occurs (compromised secret, exposed credential, unauthorized access, etc.):

### Step 1: Immediate Actions (0-15 minutes)

1. **Assess scope:**
   - Which environment? (dev, staging, production)
   - What was compromised? (secret, token, access)
   - When did it happen?

2. **Contain the threat:**
   - Rotate compromised secrets (see "Rotate Compromised Secret" above)
   - Revoke compromised tokens (see "Revoke Dev Token" above)
   - If unauthorized access: block IP addresses, disable accounts

3. **Document initial findings:**
   - Record timestamp
   - Note what was discovered
   - List immediate actions taken

### Step 2: Investigation (15-60 minutes)

1. **Review logs:**
   ```bash
   docker compose logs web | grep -i "error\|unauthorized\|failed"
   docker compose logs nginx | tail -100
   ```

2. **Check for exposed secrets:**
   - Search git history: `git log -p -S "SECRET_KEY" --all`
   - Check recent commits: `git log --oneline -10`
   - Review CI/CD logs for exposed secrets

3. **Identify root cause:**
   - How was the secret compromised?
   - Was it committed to git?
   - Exposed in logs or error messages?
   - Shared in insecure channel?

### Step 3: Remediation (1-4 hours)

1. **Fix the vulnerability:**
   - Remove secrets from git history (if committed)
   - Update `.gitignore` if needed
   - Fix code that exposed secrets
   - Update documentation/processes

2. **Rotate all potentially affected secrets:**
   - Even if not directly compromised, rotate if in same environment
   - Update CI/CD secrets
   - Notify team to update local `.env` files

3. **Verify fixes:**
   - Run security checklist
   - Test authentication flows
   - Verify no secrets in logs

### Step 4: Documentation and Follow-up (1 day)

1. **Create incident report:**
   - Date/time of incident
   - What happened
   - Root cause
   - Actions taken
   - Impact assessment

2. **Update security controls:**
   - Add new checks to this checklist if needed
   - Update `docs/security_plan.md` with lessons learned
   - Improve processes to prevent recurrence

3. **Team communication:**
   - Notify team of incident (if applicable)
   - Share lessons learned
   - Update onboarding documentation

### Incident Response Template

```markdown
## Security Incident Report

**Date:** YYYY-MM-DD HH:MM
**Reported by:** [Name]
**Severity:** Low / Medium / High / Critical

### Summary
[Brief description of what happened]

### Timeline
- **Discovery:** YYYY-MM-DD HH:MM
- **Containment:** YYYY-MM-DD HH:MM
- **Resolution:** YYYY-MM-DD HH:MM

### Root Cause
[What caused the incident]

### Impact
- **Environment:** dev / staging / production
- **Affected systems:** [List]
- **Data exposed:** [If any]

### Actions Taken
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Prevention
[What will prevent this from happening again]

### Follow-up
- [ ] Update security checklist
- [ ] Update documentation
- [ ] Team training (if needed)
```

## References

- [Security Plan](./security_plan.md) - Overall security strategy
- [Authentication Plan](./auth.md) - JWT implementation details
- [Development Environment](./dev-environment.md) - Local setup
- [CI/CD Security](./ci.md) - Secrets management in CI

## Document Maintenance

**Last Updated:** 2026-01-26  
**Next Review:** 2026-04-26

This checklist should be updated when:
- New security controls are added
- Incident reveals gaps
- Team feedback suggests improvements
- Security requirements change

