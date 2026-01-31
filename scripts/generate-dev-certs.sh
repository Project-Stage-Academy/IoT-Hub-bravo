#!/bin/bash
# Generate development TLS certificates using mkcert

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"

echo "Generating development TLS certificates..."

command -v mkcert >/dev/null 2>&1 || {
    echo "Error: mkcert is not installed."
    echo "Install it: https://github.com/FiloSottile/mkcert#installation"
    exit 1
}

echo "Installing local CA..."
if ! mkcert -install; then
    echo "Error: Failed to install local CA with mkcert."
    exit 1
fi

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "Generating certificates for localhost..."
if ! mkcert localhost 127.0.0.1 ::1; then
    echo "Error: Failed to generate certificates with mkcert."
    exit 1
fi

if [ ! -f "localhost+2.pem" ] || [ ! -f "localhost+2-key.pem" ]; then
    echo "Error: Expected certificate files not found. mkcert may have failed."
    exit 1
fi

mv localhost+2.pem localhost.pem
mv localhost+2-key.pem localhost-key.pem

echo "✓ Certificates generated successfully!"
echo "  - Certificate: $CERTS_DIR/localhost.pem"
echo "  - Private key: $CERTS_DIR/localhost-key.pem"