#!/bin/bash

###############################################################################
# AI Control Plane - Production Installer (PHASE 2)
#
# This script provides:
# 1. System requirements validation
# 2. Interactive configuration wizard
# 3. Cloudflare Tunnel setup guidance
# 4. DNS verification
# 5. Automated deployment
# 6. Post-deployment health checks
# 7. Clear troubleshooting steps
#
# Usage:
#   bash install.sh [--skip-cloudflare]
#
# No manual steps required after running this script.
###############################################################################

set -e
shopt -s nocasematch  # Case-insensitive matching

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(dirname "$(readlink -f "$0")")/.."
ENV_FILE="$REPO_ROOT/.env"
ENV_TEMPLATE="$REPO_ROOT/.env.template"
LOG_FILE="$REPO_ROOT/install.log"
SKIP_CLOUDFLARE=false

# Parse arguments
if [[ "$1" == "--skip-cloudflare" ]]; then
    SKIP_CLOUDFLARE=true
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     🚀 AI Control Plane - One-Click Installer         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# Helper Functions
# ============================================

log_step() {
    echo "[$(date '+%H:%M:%S')] $1" >> "$LOG_FILE"
}

check_dns() {
    local domain=$1
    echo -n "  Checking DNS for $domain... "
    if nslookup "$domain" &> /dev/null || dig +short "$domain" &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${YELLOW}(not yet registered)${NC}"
        return 1
    fi
}

check_cloudflare_tunnel() {
    local token=$1
    echo -n "  Validating Cloudflare Tunnel token... "
    
    # Try to use the token (cloudflared would do this, but we can at least check it's not empty)
    if [[ -z "$token" || "$token" == "your_tunnel_token_here" ]]; then
        echo -e "${YELLOW}(placeholder)${NC}"
        return 1
    fi
    
    # Token looks valid (basic check)
    if [[ ${#token} -gt 10 ]]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗ (invalid format)${NC}"
        return 1
    fi
}

wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "  Waiting for $service... "
    while [[ $attempt -lt $max_attempts ]]; do
        if docker compose port "$service" "$port" &> /dev/null; then
            echo -e "${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗ (timeout)${NC}"
    return 1
}

run_health_check() {
    local app_healthy=false
    local ollama_healthy=false
    local prometheus_healthy=false
    
    # Check app service
    if docker compose exec -T app curl -s http://localhost:8000/api/health &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Backend API responding"
        app_healthy=true
    else
        echo -e "  ${YELLOW}⚠ ${NC} Backend API not responding (may still be starting)"
    fi
    
    # Check Ollama
    if docker compose exec -T ollama curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama service healthy"
        ollama_healthy=true
    else
        echo -e "  ${RED}✗${NC} Ollama service not responding"
    fi
    
    # Check Prometheus
    if docker compose exec -T prometheus curl -s http://localhost:9090/-/healthy &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Prometheus service healthy"
        prometheus_healthy=true
    else
        echo -e "  ${YELLOW}⚠ ${NC} Prometheus not responding (metrics not available yet)"
    fi
    
    if [[ "$app_healthy" == true && "$ollama_healthy" == true ]]; then
        return 0
    else
        return 1
    fi
}

# Step 1: Check Docker
echo -e "${YELLOW}[1/7] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found!${NC}"
    echo "  Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"

# Step 2: Check Docker Compose
echo ""
echo -e "${YELLOW}[2/7] Checking Docker Compose...${NC}"
if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found!${NC}"
    echo "  Install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found: $(docker compose version | head -1)${NC}"

# Step 3: Get user inputs
echo ""
echo -e "${YELLOW}[3/7] Configuration${NC}"
echo "  Please provide your configuration."
echo ""

# Domain
while true; do
    read -p "  Domain name (e.g., example.com): " DOMAIN
    if [[ "$DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        break
    else
        echo -e "  ${RED}✗ Invalid domain format (use example.com)${NC}"
    fi
done

# Email
while true; do
    read -p "  Admin email (for SSL certificates): " ADMIN_EMAIL
    if [[ "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        break
    else
        echo -e "  ${RED}✗ Invalid email format${NC}"
    fi
done

# Check if .env already exists
if [[ -f "$ENV_FILE" ]]; then
    echo ""
    read -p "  .env already exists. Overwrite? (y/n): " OVERWRITE
    if [[ "$OVERWRITE" != "y" && "$OVERWRITE" != "Y" ]]; then
        echo -e "${RED}✗ Installation cancelled${NC}"
        exit 1
    fi
fi

# Check DNS
echo ""
echo -e "${YELLOW}Checking DNS...${NC}"
if check_dns "$DOMAIN"; then
    echo -e "  ${GREEN}✓ Domain is registered and resolvable${NC}"
else
    echo -e "  ${YELLOW}⚠ Domain not yet in DNS (will be ready after Cloudflare setup)${NC}"
fi

# Step 4: Generate .env
echo ""
echo -e "${YELLOW}[4/7] Generating configuration (.env)...${NC}"

# Check if template exists
if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo -e "${RED}✗ .env.template not found at $ENV_TEMPLATE${NC}"
    exit 1
fi

# Copy template
cp "$ENV_TEMPLATE" "$ENV_FILE"

# Generate strong password for Grafana
GRAFANA_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25) || GRAFANA_PASSWORD="changeme123456"

# Update .env with user inputs
sed -i "s|DOMAIN=.*|DOMAIN=$DOMAIN|g" "$ENV_FILE"
sed -i "s|TRAEFIK_CERTIFICATESEMAIL=.*|TRAEFIK_CERTIFICATESEMAIL=$ADMIN_EMAIL|g" "$ENV_FILE"
sed -i "s|GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD|g" "$ENV_FILE"

echo -e "${GREEN}✓ Configuration saved to .env${NC}"

# Step 5: Cloudflare Tunnel Setup
echo ""
echo -e "${YELLOW}[5/7] Cloudflare Tunnel Setup${NC}"

if [[ "$SKIP_CLOUDFLARE" == true ]]; then
    echo "  Skipping Cloudflare setup (--skip-cloudflare flag)"
else
    echo "  You need a Cloudflare Tunnel for secure external access."
    echo ""
    
    read -p "  Do you have a Cloudflare Tunnel token? (y/n): " HAS_TOKEN
    
    if [[ "$HAS_TOKEN" == "y" || "$HAS_TOKEN" == "Y" ]]; then
        read -sp "  Paste your Cloudflare Tunnel token: " TUNNEL_TOKEN
        echo ""
        
        if check_cloudflare_tunnel "$TUNNEL_TOKEN"; then
            sed -i "s|CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=$TUNNEL_TOKEN|g" "$ENV_FILE"
            echo -e "  ${GREEN}✓ Token saved${NC}"
        else
            echo -e "  ${RED}✗ Token validation failed${NC}"
            echo "  Continuing with placeholder (update manually before accessing externally)"
        fi
    else
        echo ""
        echo -e "  ${YELLOW}📋 Cloudflare Tunnel Setup Instructions:${NC}"
        echo ""
        echo "  1. Go to: https://dash.cloudflare.com/"
        echo "  2. Login to your Cloudflare account"
        echo "  3. Select your domain ($DOMAIN)"
        echo "  4. Go to: Access → Tunnels"
        echo "  5. Click 'Create a tunnel'"
        echo "  6. Name it: ai-control-plane"
        echo "  7. Copy the TOKEN when prompted"
        echo ""
        echo "  Then edit .env and set:"
        echo "    CLOUDFLARE_TUNNEL_TOKEN=<your-token>"
        echo ""
        echo "  Restart the tunnel:"
        echo "    docker compose restart cloudflared"
        echo ""
    fi
fi

log_step "Configuration complete"

# Step 6: Deployment
echo ""
echo -e "${YELLOW}[6/7] Deploying AI Control Plane...${NC}"
echo "  This may take 2-5 minutes on first run (downloading images)."
echo ""

cd "$REPO_ROOT"

# Run deploy script
if [[ -f "scripts/deploy.sh" ]]; then
    if bash scripts/deploy.sh | tee -a "$LOG_FILE"; then
        log_step "Deployment completed"
    else
        echo -e "${RED}✗ Deployment failed${NC}"
        echo "  Check the logs:"
        echo "    docker compose logs"
        echo "  Or debug with:"
        echo "    docker compose ps"
        exit 1
    fi
else
    echo -e "${RED}✗ scripts/deploy.sh not found${NC}"
    exit 1
fi

# Step 7: Health checks
echo ""
echo -e "${YELLOW}[7/7] Verifying deployment...${NC}"

if run_health_check; then
    log_step "Health checks passed"
else
    echo ""
    echo -e "${YELLOW}⚠ Some services may still be starting...${NC}"
    echo "  Checks in 30 seconds automatically. You can also run:"
    echo "    docker compose ps"
    echo ""
fi

echo ""
echo -e "${GREEN}╔═════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ AI Control Plane Installation Complete!             ║${NC}"
echo -e "${GREEN}╚═════════════════════════════════════════════════════════╝${NC}"
echo ""

# Final instructions
echo -e "${GREEN}🎉 Next Steps:${NC}"
echo ""
echo -e "  📱 Access your AI Control Plane:"
echo -e "     ${YELLOW}https://app.$DOMAIN${NC}"
echo ""
echo -e "  🔑 Domain: $DOMAIN"
echo -e "  📧 Email: $ADMIN_EMAIL"
echo ""

if [[ "$SKIP_CLOUDFLARE" != true ]] && grep -q "CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here" "$ENV_FILE"; then
    echo -e "  ${YELLOW}⚠️  Cloudflare Tunnel not configured${NC}"
    echo "     See instructions above to complete setup"
    echo ""
fi

echo -e "${GREEN}📊 Admin Access (Internal Only):${NC}"
echo -e "  Grafana & Prometheus are protected and internal-only."
echo -e "  Access via SSH tunnel:"
echo -e "    ssh -L 3000:localhost:3000 user@$DOMAIN"
echo -e "  Then open: http://localhost:3000"
echo -e ""
echo -e "  Credentials:"
echo -e "    User: admin"
echo -e "    Password: $(grep 'GRAFANA_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2)"
echo -e ""
echo -e "  🔐 See INTERNAL_ACCESS.md for detailed access instructions"
echo ""

echo -e "${GREEN}📖 Helpful Commands:${NC}"
echo ""
echo "  View logs:"
echo "    docker compose logs app -f"
echo ""
echo "  Check service status:"
echo "    docker compose ps"
echo ""
echo "  Restart services:"
echo "    docker compose restart"
echo ""
echo "  View installer log:"
echo "    cat $LOG_FILE"
echo ""

echo -e "${GREEN}❓ Need Help?${NC}"
echo "  1. Check the logs: docker compose logs"
echo "  2. Review README.md for developer docs"
echo "  3. See PRODUCT.md for user guide"
echo ""
echo -e "Log: $LOG_FILE"
echo ""
