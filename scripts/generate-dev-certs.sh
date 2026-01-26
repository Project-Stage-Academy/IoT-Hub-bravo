#!/bin/bash
# Generate development TLS certificates using mkcert

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"

echo "Generating development TLS certificates..."

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo "Error: mkcert is not installed."
    echo "Install it: https://github.com/FiloSottile/mkcert#installation"
    exit 1
fi

# Install local CA (if not already installed)
echo "Installing local CA..."
mkcert -install

# Create certs directory
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# Generate certificates
echo "Generating certificates for localhost..."
mkcert localhost 127.0.0.1 ::1

# Rename to match nginx config
if [ -f "localhost+2.pem" ]; then
    mv localhost+2.pem localhost.pem
    mv localhost+2-key.pem localhost-key.pem
    echo "✓ Certificates generated successfully!"
    echo "  - Certificate: $CERTS_DIR/localhost.pem"
    echo "  - Private key: $CERTS_DIR/localhost-key.pem"
else
    echo "Error: Certificate generation failed"
    exit 1
fi

