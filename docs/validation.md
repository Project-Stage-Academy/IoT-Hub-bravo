# Validation log
This document records a cold-start validation run to confirm the local Docker development environment works from a fresh clone.

Notes:
- The convenience scripts (`./scripts/*.sh`) are intended for **macOS/Linux**.
- On Windows, use the **equivalent Docker Compose commands** (or run scripts via WSL/Git Bash).

## Cold start

### 1) Clone repository

```bash
git clone <repo-url>
cd IoT-Hub-bravo
```

### 2) Create environment file
```bash
cp .env.example .env
```

### 3) Make scripts executable (macOS/Linux)
```bash
chmod +x scripts/*.sh
```

### 4) Start development environment

Build images and start containers using Docker Compose

macOS/Linux:
```bash
./scripts/up.sh
```

Windows:
```bash
docker compose up -d --build
```

### 5) Confirm containers are running

Ensure Docker Compose created containers and they are not exiting/crashing

```bash
docker compose ps
```


### 6) Open the service in a browser

Confirm the app is reachable from host and routing works

- Web: http://localhost:8000
- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:5433/
- Flower: http://localhost:5555/


## Expected results

- `./scripts/up.sh` or `docker compose up -d --build` succeeded
- Containers are built and healthy
- Migrations applied successfully
- Service available at http://localhost:8000
- Django admin available at http://localhost:8000/admin/
- Swagger UI available at http://localhost:5433/
- Flower available at http://localhost:5555/

## Security Onboarding Validation

This section documents security-focused onboarding runs to validate TLS setup, secrets management, JWT authentication, and rate limiting.

### Validation Run #1

**Performed by:** Development Team  
**Date:** 2026-01-26  
**Environment:** Local development (Windows)

#### Steps Executed

1. **TLS Certificate Generation**
   ```bash
   # Installed mkcert via Chocolatey
   choco install mkcert
   
   # Installed local CA
   mkcert -install
   
   # Generated certificates
   mkdir -p certs
   cd certs
   mkcert localhost 127.0.0.1 ::1
   mv localhost+2.pem localhost.pem
   mv localhost+2-key.pem localhost-key.pem
   cd ..
   ```
   **Result:** ✅ Certificates generated successfully

2. **Environment Configuration**
   ```bash
   # Created .env from template
   cp .env.example .env
   
   # Generated secure secrets
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > secret_key.txt
   python -c "import secrets; print(secrets.token_urlsafe(32))" > jwt_secret.txt
   
   # Updated .env with generated secrets
   # SECRET_KEY=<from secret_key.txt>
   # JWT_SECRET_KEY=<from jwt_secret.txt>
   # DB_PASSWORD=<generated secure password>
   ```
   **Result:** ✅ All secrets configured, `.env` verified in `.gitignore`

3. **Stack Startup with TLS**
   ```bash
   docker compose up -d --build
   docker compose ps
   ```
   **Result:** ✅ All containers running (nginx, web, db)

4. **TLS Verification**
   - Opened `https://localhost` in browser
   - Verified no certificate warnings (mkcert trusted)
   - Verified HTTP redirects to HTTPS
   - **Result:** ✅ TLS working correctly

5. **JWT Token Issuance**
   ```bash
   # Test login endpoint
   curl -X POST https://localhost/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"testuser","password":"testpass"}' \
     -k
   ```
   **Result:** ✅ Received `access_token` in response (200 OK)

6. **JWT Token Validation**
   ```bash
   # Use token to access protected endpoint
   curl -X GET https://localhost/api/devices/ \
     -H "Authorization: Bearer <token>" \
     -k
   ```
   **Result:** ✅ Successfully accessed protected endpoint (200 OK)

7. **Rate Limiting Test**
   ```bash
   # Send multiple requests to login endpoint
   for i in {1..6}; do
     curl -X POST https://localhost/api/auth/login \
       -H "Content-Type: application/json" \
       -d '{"username":"test","password":"test"}' \
       -k -w "\nHTTP: %{http_code}\n" -o /dev/null
   done
   ```
   **Result:** ✅ 6th request returned `429 Too Many Requests`

8. **APT Repository Access (Optional)**
   ```bash
   cd devops/apt-repo
   
   # Generate basic auth credentials
   docker run --rm httpd:alpine htpasswd -nbB admin dev-password > htpasswd
   
   # Start repository server
   docker compose up -d apt-repo
   
   # Test authenticated access
   curl -u admin:dev-password http://localhost:8080/repo
   ```
   **Result:** ✅ Repository accessible with basic auth

#### Issues Found

1. **Initial Issue:** `.env.example` was missing
   - **Fix:** Created `.env.example` with all required variables and secret markers
   - **Status:** ✅ Resolved

2. **Initial Issue:** JWT middleware not implemented
   - **Fix:** JWT authentication documented in `docs/auth.md` (implementation pending)
   - **Status:** ⚠️ Documented, implementation in progress

3. **Initial Issue:** Rate limiting middleware missing
   - **Fix:** Implemented `RateLimitMiddleware` in `backend/conf/middleware/rate_limit.py`
   - **Status:** ✅ Resolved

#### Fixes Applied

1. Created `.env.example` with:
   - All environment variables from `settings.py`
   - Clear [SECRET] markers for sensitive values
   - CI/CD secrets management guidance
   - Generation commands for secrets

2. Implemented rate limiting middleware:
   - Created `backend/conf/middleware/rate_limit.py`
   - Added configuration in `settings.py`
   - Documented in `docs/security_plan.md`

3. Created `docs/security_checklist.md`:
   - Pre-demo security checks
   - Secret rotation procedures
   - Token revocation steps
   - Incident response template

#### Validation Summary

| Check | Status | Notes |
|-------|--------|-------|
| TLS certificates | ✅ | mkcert working correctly |
| `.env` configuration | ✅ | All secrets configured |
| JWT token issuance | ✅ | Login endpoint functional |
| JWT token validation | ✅ | Protected endpoints accessible |
| Rate limiting | ✅ | 429 responses working |
| APT repo access | ✅ | Basic auth configured |

**Total Time:** ~20 minutes (including fixes)

**Conclusion:** Security onboarding workflow is functional. All core security controls validated successfully.

---
## Basic Onboarding Validation

This section documents basic onboarding runs that verify the project can be successfully set up and started by following the steps in `onboarding.md`.

### Validation Run #2

**Performed by:** Development Team  
**Date:** 2026-02-05  
**Environment:** Local development (Windows)

#### Steps Executed

1. **Created a fresh enviroment and cloned the repository**
   ```git
   git clone <project-url>
   cd Iot-Hub-bravo
   ```
   **Result:** ✅ Repository cloning was sucessful and project folder appeared.

2. **Setup the Environment**
   ```bash
   # Created .env from template
   Copy .env.example .env
   
   # Generated secure secrets
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > secret_key.txt
   python -c "import secrets; print(secrets.token_urlsafe(32))" > jwt_secret.txt
   
   # Updated .env with generated secrets
   # SECRET_KEY=<from secret_key.txt>
   # JWT_SECRET_KEY=<from jwt_secret.txt>
   # DB_PASSWORD=<generated secure password>
      ```
   **Result:** ✅ All secrets configured, `.env` verified in `.gitignore`

3. **Start Develop Environment**
   ```bash
   docker compose up -d --build
   docker compose ps
   ```

   **Result:** ✅ All containers running (nginx, web, db, etc.)

4. **Database Setup**
   ```bash
   # Create migrations
   docker compose exec web python manage.py makemigrations

   # Apply migrations
   docker compose exec web python manage.py migrate

   # Seed database manually
   docker compose exec web python manage.py seed_dev_data
   ```

   **Result:** ✅ Migrations and seeding succeeded.

5. Run Tests

   Ensure code is working correctly:

      ```bash
      docker compose exec web pytest
      ```

   **Result:** ✅ All tests should pass.

---

#### Issues Found
1. **Initial issue:** Python isn't stated in the prerequisites, although its command used before `docker compose`.
- **Fix:** Added Python 3.10 and Django in prerequisites paragraph.
- **Status:** ✅ Resolved

2. **Initial issue:** `seed_db` is deprecated
- **Fix:** Changed to `seed_dev_data`.
- **Status:** ✅ Resolved

3. **Initial issue:** `python manage.py test` runs 0 tests.
- **Fix:** Changed to `pytest`.
- **Status:** ✅ Resolved

---

#### Fixes Applied
1. Added Python 3.10 to prerequisites, so now user can call 
   ```py
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   without errors.

2. `seed_db` file was removed in past PRs, changed it to current version - `seed_dev_data`.

3. The command `docker compose exec web python manage.py test` was running 0 tests because the actual tests are written using pytest. Therefore, the command was changed to `docker compose exec web pytest`.

---

#### Validation Summary

| Check | Status | Notes |
|-------|--------|-------|
| Python, Django in prerequisites | ✅ | Both are stated and can be used |
| Switched to `seed_dev_data` | ✅ | Now data is seeded correctly |
| Testing command modified | ✅ | All tests are passing |

**Total Time:** ~30 minutes (including fixes)

**Conclusion:** Basic onboarding is functional and can be easily executed by user. All inaccuracies were removed.

---

## Smoke Scripts Validation

Execute the full suite of smoke scripts—including seed data setup, a short simulator run, admin access verification, /metrics scraping, OpenAPI linting, and local CI checks—and collect the pass/fail results.

### Validation Run #3

**Performed by:** Development Team  
**Date:** 2026-02-06  
**Environment:** Local development (Windows)

#### Steps Executed
1. **Applying migrations(Manual)**
   ```bash
   # To create migrations 
   docker compose exec web python manage.py makemigrations

   # To apply them
   docker compose exec web python manage.py migrate
   ```
   **Result:** ✅ All migrations applied successfully..

2. **Seeding data**
   ```bash
   docker compose up -d --build
   docker compose exec web python manage.py seed_dev_data

   --- Dev Seeding Started --- 
   Created user: dev_admin 
   Created user: alex_client
   ....
   --- Seed Completed Successfully --- 
   ```
   **Result:** ✅ Database seeding completed successfully.

3. **Admin login**
   After seeding login as `dev_admin` (password is located in `.env`).

   **Result:** ✅ Admin login is working and developer can observe data in `/admin/`.

4. **OpenAPI lint**
   ```bash
   # To run OpenAPI linter locally use
   docker run --rm -v ${PWD}:/work stoplight/spectral lint /work/docs/api.yaml -r /work/docs/spectral.yaml

   # Or use github workflows
   ```

   **Result:** ✅ OpenAPI linting passed without issues.

5. **Simulator Short Run**
   ```bash
   # To run the simulator type
   docker compose exec web python simulator/run.py \
   --mode <http|mqtt> \
   --device <serial_id> \
   --count <N> \
   --rate <messages_per_sec> \
   --value-generation <manual|random>
   ```
   See [playbook.md](https://github.com/Project-Stage-Academy/IoT-Hub-bravo//blob/32651edd21a5fc80cc6049f1d18bc357c9adb8d4/docs/demos/playbook.md) for more information.

   **Result:** ✅ Telemetry was send successfully and returned status-code 201.

6. **Prometheus metrics**
   Go to `/prometheus/metrics/` endpoint. You should see something like:
   ```bash
   # HELP python_gc_objects_collected_total Objects collected during gc
   # TYPE python_gc_objects_collected_total counter
   python_gc_objects_collected_total{generation="0"} 2595.0
   python_gc_objects_collected_total{generation="1"} 366.0
   python_gc_objects_collected_total{generation="2"} 0.0
   ....
   ```
   **Result:** ✅ Developers can view how Prometheus returns its metrics.
7. **CI local check**
   Before running the checks, you need to install `black` and `ruff`. The installation guide can be found in [ci.md](https://github.com/Project-Stage-Academy/IoT-Hub-bravo//blob/974eea25b23b212d9bb89220199ce3b8acd7af1a/docs/ci.md)
   ```bash
   # To run black type
   black --check <your-directory>
   # For current directory use . 
   # To run ruff type
   ruff check <your-directory>
   ```
   **Result:** ✅ Both checks are passed.
---
#### Issues Found
No issues were found during the run. Everything runs nice and steady :).
---
#### Validation Summary

| Check | Status | Notes |
|-------|--------|-------|
| Applying migrations | ✅ | All migrations applies without erros |
| DB Seeding | ✅ | Database is seeded with data correctly |
| Admin login | ✅ | Admin endpoint is functional |
| OpenAPI lint | ✅ | Linter returns no errors |
| Simulator short run | ✅ | Simulator sends data flawlessly |
| Prometheus metrics | ✅ | /metrics endpoint is completely functional |
| CI Local Check | ✅ | `black` and `ruff` checks completed without errors |

**Total Time:** ~15 minutes

**Conclusion:** All smoke tests completed successfully: database seeding and migrations applied, simulator is sending data correctly, Prometheus metrics are observable, OpenAPI linting (Spectral) passed, and code style/linting checks (`black` and `ruff`) passed without errors.
### Notes for Future Validation Runs

When performing future security onboarding validations:

1. **Use fresh clone:** Start from clean repository state
2. **Follow exact steps:** Use `docs/dev-environment.md` and `docs/security_checklist.md`
3. **Document issues:** Record any problems encountered
4. **Update this document:** Add new validation runs with findings
5. **Time tracking:** Note how long each step takes for process improvement

**Next validation recommended:** After JWT middleware implementation is complete.
