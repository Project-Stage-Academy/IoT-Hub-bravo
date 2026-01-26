# Developer environment

This repository provides a reproducible local developer environment for the monolithic MVP using Docker and Docker Compose.


## Requirements

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose
- Git


## Compose files and intended usage

Two Compose files are used:

- `docker-compose.yml` — **base** configuration (Gunicorn, no live code mounts).
- `docker-compose.override.yml` — **development override** (bind-mount source code into the container and run Django `runserver`).

Docker Compose automatically loads `docker-compose.override.yml` when you run `docker compose ...` without `-f`.

**Security note**: `docker/django/Dockerfile` defines build-time `SECRET_KEY` environment variable,
which is an intentionally unsafe placeholder used only for `collectstatic` command. 
Runtime must supply a real secret key. Do not reuse the build placeholder in any environment.


### Base run
`docker compose -f docker-compose.yml up -d --build`


### Development run
Loads docker-compose.override.yml automatically and bind-mounts the source code

`docker compose up -d --build`


### What changes in dev mode
- command is replaced with `python manage.py runserver 0.0.0.0:8000`
- `./backend` is mounted into `/app` inside the container for live code reload
- `static_data` named volume is mounted

## TLS Setup for Local Development

The development environment uses nginx as a reverse proxy to terminate TLS connections. This allows testing HTTPS locally without browser certificate warnings.

### Prerequisites

Install `mkcert` (recommended) or use OpenSSL for self-signed certificates.

#### Option 1: Using mkcert (Recommended)

**Installation:**

- **macOS**: `brew install mkcert`
- **Windows**: `choco install mkcert` or download from [mkcert releases](https://github.com/FiloSottile/mkcert/releases)
- **Linux**: 
  ```bash
  # Install certutil
  sudo apt install libnss3-tools  # Ubuntu/Debian
  # or
  sudo yum install nss-tools      # RHEL/CentOS
  
  # Install mkcert
  curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
  chmod +x mkcert-v*-linux-amd64
  sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
  ```

**Generate and trust certificates:**

```bash
# Install local CA
mkcert -install

# Generate certificate for localhost
mkdir -p certs
cd certs
mkcert localhost 127.0.0.1 ::1

# Rename files to match nginx config
mv localhost+2.pem localhost.pem
mv localhost+2-key.pem localhost-key.pem
cd ..
```

**Verify:**
- `localhost.pem` and `localhost-key.pem` should be in `certs/` directory
- Browser should trust the certificate automatically (mkcert installs local CA)

#### Option 2: Using OpenSSL (Self-signed)

If you cannot use mkcert, generate self-signed certificates:

```bash
mkdir -p certs
cd certs

# Generate private key
openssl genrsa -out localhost-key.pem 2048

# Generate certificate signing request
openssl req -new -key localhost-key.pem -out localhost.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in localhost.csr -signkey localhost-key.pem \
  -out localhost.pem

# Clean up CSR
rm localhost.csr
cd ..
```

**Note**: Self-signed certificates will show browser warnings. You'll need to manually trust them:
- **Chrome/Edge**: Click "Advanced" → "Proceed to localhost (unsafe)"
- **Firefox**: Click "Advanced" → "Accept the Risk and Continue"

### Starting Services with TLS

1. **Generate certificates** (if not already done):
   ```bash
   # Using mkcert (recommended)
   mkcert -install
   mkdir -p certs
   cd certs
   mkcert localhost 127.0.0.1 ::1
   mv localhost+2.pem localhost.pem
   mv localhost+2-key.pem localhost-key.pem
   cd ..
   ```

2. **Start services**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify TLS**:
   - Open browser: `https://localhost`
   - Should see Django application without certificate errors (if using mkcert)
   - HTTP requests to `http://localhost` will redirect to HTTPS

### Troubleshooting

**Certificate errors in browser:**
- If using mkcert: Ensure `mkcert -install` was run successfully
- If using OpenSSL: Manually trust the certificate in browser settings
- Verify certificates exist: `ls -la certs/`

**nginx container fails to start:**
- Check certificates are in `certs/` directory with correct names
- Verify file permissions: `chmod 644 certs/localhost.pem` and `chmod 600 certs/localhost-key.pem`
- Check nginx logs: `docker compose logs nginx`

**Cannot access https://localhost:**
- Verify nginx container is running: `docker compose ps`
- Check nginx is listening on port 443: `docker compose logs nginx`
- Verify port 443 is not used by another service: `netstat -an | grep 443` (Linux/macOS)

**Django app not accessible through nginx:**
- Verify web container is running: `docker compose ps`
- Check web container logs: `docker compose logs web`
- Test direct connection (if web port is still exposed): `curl http://localhost:8000`

### Certificate Renewal

**mkcert certificates**: Valid for a long time (typically 825 days). No renewal needed for dev.

**OpenSSL self-signed**: Regenerate when expired (365 days default):
```bash
# Regenerate using same commands as above
```

### Security Notes

- **Dev certificates only**: These certificates are for local development only
- **Never commit certificates**: The `certs/` directory should be in `.gitignore`
- **Staging/Production**: Use proper certificates (Let's Encrypt, internal CA) in staging/production