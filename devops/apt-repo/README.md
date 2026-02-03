# Internal APT Repository

This directory contains a development stub for an internal APT repository used for packaging IoT Hub services as `.deb` packages.

## Overview

The repository uses `reprepro` to manage Debian packages and `nginx` to serve them over HTTP with basic authentication and network restrictions.

## Quick Start

### 1. Generate Basic Auth Credentials

Create `.htpasswd` file for nginx authentication:

```bash
docker run --rm httpd:alpine htpasswd -nbB admin your-secure-password > htpasswd
```

Or using `htpasswd` locally:

```bash
htpasswd -c htpasswd admin
```

**Security Note**: Never commit `htpasswd` to version control. Add it to `.gitignore`.

### 2. Initialize Repository Structure

```bash
mkdir -p repo/conf incoming
```

Create `repo/conf/distributions`:

```
Origin: IoT Hub Internal
Label: IoT Hub Internal Repository
Suite: stable
Codename: stable
Architectures: amd64 arm64
Components: main
Description: Internal APT repository for IoT Hub services
SignWith: default
```

### 3. Start Repository Server

```bash
docker compose up -d apt-repo
```

The repository will be available at `http://localhost:8080/repo` (or port specified in `APT_REPO_PORT`).

### 4. Add Packages

Place `.deb` files in `incoming/` directory, then run:

```bash
docker compose run --rm reprepro
```

This will:
- Import packages from `incoming/` into the repository
- Update repository metadata
- Make packages available via HTTP

### 5. Configure Clients

Add repository to `/etc/apt/sources.list.d/iot-hub.list`:

```
deb http://apt-repo-server:8080/repo stable main
```

For authenticated access, create `/etc/apt/auth.conf`:

```
machine apt-repo-server:8080
login admin
password your-secure-password
```

Update package list:

```bash
apt-get update
```

## Security Configuration

### Basic Authentication

The nginx configuration enforces HTTP Basic Authentication using `.htpasswd`. Credentials are required for all repository access.

**Development**: Use simple passwords for local testing.  
**Staging/Production**: Use strong passwords and rotate regularly.

### Network Restrictions

The nginx configuration restricts access to private network ranges:

- `172.16.0.0/12` (Docker networks)
- `192.168.0.0/16` (Private networks)
- `10.0.0.0/8` (Private networks)

All other IPs are denied.

**To modify restrictions**, edit `nginx.conf`:

```nginx
allow 192.168.1.0/24;
deny all;
```

### Additional Security Options

1. **TLS/HTTPS**: Add SSL certificates and configure HTTPS in `nginx.conf`
2. **IP Whitelist**: Restrict to specific IPs in staging/production
3. **VPN Access**: Require VPN connection for repository access
4. **GPG Signing**: Sign repository metadata with GPG keys

## Directory Structure

```
devops/apt-repo/
├── docker-compose.yml      # Service definitions
├── nginx.conf              # Nginx configuration
├── README.md               # This file
├── repo/                   # Repository data (generated)
│   ├── conf/              # reprepro configuration
│   └── ...
├── incoming/              # Place .deb files here
└── htpasswd              # Basic auth credentials (gitignored)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APT_REPO_PORT` | `8080` | HTTP port for repository server |
| `APT_REPO_NAME` | `iot-hub-internal` | Repository name |

Set in `.env` or `docker-compose.override.yml`:

```yaml
services:
  apt-repo:
    environment:
      - APT_REPO_PORT=9000
```

## Troubleshooting

**Repository not accessible:**
- Check nginx container logs: `docker compose logs apt-repo`
- Verify network restrictions allow your IP
- Ensure `.htpasswd` file exists and has correct permissions

**Packages not appearing:**
- Verify `.deb` files are in `incoming/` directory
- Check reprepro logs: `docker compose logs reprepro`
- Ensure `repo/conf/distributions` is correctly configured

**Authentication fails:**
- Regenerate `.htpasswd` file
- Verify credentials in `/etc/apt/auth.conf` match `.htpasswd`
- Check nginx error logs for authentication failures

## Integration with CI/CD

To publish packages from CI/CD pipeline:

1. Build `.deb` package in CI job
2. Upload package artifact
3. Deploy to repository server using:
   ```bash
   scp package.deb repo-server:/path/to/incoming/
   ssh repo-server 'cd /path/to/repo && docker compose run --rm reprepro'
   ```

Or use repository API if implemented.

## References

- [reprepro documentation](https://mirrorer.alioth.debian.org/)
- [nginx HTTP Basic Auth](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html)
- [Debian Repository Howto](https://wiki.debian.org/HowToSetupADebianRepository)



