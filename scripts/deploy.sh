#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 GururajSeethur Infra - Deployment Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .env exists
if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "❌ .env file not found!"
    echo "📋 Creating .env from template..."
    cp "$REPO_ROOT/.env.template" "$REPO_ROOT/.env"
    echo "⚠️  IMPORTANT: Edit .env and set:"
    echo "   - CLOUDFLARE_TUNNEL_TOKEN"
    echo "   - DOMAIN"
    echo "   - GRAFANA_ADMIN_PASSWORD"
    echo ""
    echo "Then run: $0"
    exit 1
fi

# Generate Traefik dynamic.yml from template using htpasswd
if command -v htpasswd >/dev/null 2>&1; then
    echo "Generating Traefik dynamic configuration with basic auth..."
    source "$REPO_ROOT/.env"
    if [ -z "${TRAEFIK_BASIC_AUTH_USER}" ] || [ -z "${TRAEFIK_BASIC_AUTH_PASSWORD}" ]; then
        echo "TRAEFIK_BASIC_AUTH_USER or TRAEFIK_BASIC_AUTH_PASSWORD not set in .env; using defaults from .env.template"
    fi
    BASIC_AUTH_ENTRY=$(htpasswd -nbB "${TRAEFIK_BASIC_AUTH_USER}" "${TRAEFIK_BASIC_AUTH_PASSWORD}" | tr -d '\n')
    sed "s#__TRAEFIK_BASIC_AUTH_HASH__#${BASIC_AUTH_ENTRY}#g" "$REPO_ROOT/config/traefik/dynamic.yml.template" > "$REPO_ROOT/config/traefik/dynamic.yml"
else
    echo "htpasswd not found; skipping Traefik dynamic.yml generation. Install apache2-utils (Deb/Ubuntu) or httpd-tools (RHEL/CentOS)."
fi

# Source environment
set -a
source "$REPO_ROOT/.env"
set +a

# Validate required variables
if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] || [ "$CLOUDFLARE_TUNNEL_TOKEN" = "your_tunnel_token_here" ]; then
    echo "❌ CLOUDFLARE_TUNNEL_TOKEN not configured in .env"
    exit 1
fi

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "gururajseethur.in" ] && grep -q "your_tunnel_token_here" "$REPO_ROOT/.env"; then
    echo "❌ Configuration incomplete. Update .env first."
    exit 1
fi

echo "✅ Configuration validated"
echo "   Domain: $DOMAIN"
echo "   Tunnel: $(echo $CLOUDFLARE_TUNNEL_TOKEN | cut -c1-10)..."

# Create required directories
mkdir -p "$REPO_ROOT/config/traefik"
touch "$REPO_ROOT/config/traefik/acme.json"
chmod 600 "$REPO_ROOT/config/traefik/acme.json"

echo "📦 Building custom containers..."
cd "$REPO_ROOT"
docker-compose build --no-cache

echo "🐳 Starting services..."
docker-compose up -d

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Access your dashboard:"
echo "   🔗 https://dashboard.$DOMAIN (Grafana)"
echo "   🔗 https://prometheus.$DOMAIN (Prometheus)"
echo "   🔗 https://ollama.$DOMAIN (Ollama API)"
echo ""
echo "⏳ Services starting up (1-2 minutes)..."
echo "   Check status: docker-compose ps"
echo "   View logs: docker-compose logs -f"
echo ""
echo "🔐 Default credentials:"
echo "   Username: admin"
echo "   Password: (from .env GRAFANA_ADMIN_PASSWORD)"
echo ""
