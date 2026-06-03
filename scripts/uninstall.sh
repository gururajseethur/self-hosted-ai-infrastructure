#!/bin/bash

###############################################################################
# AI Control Plane - Uninstall Script
#
# Cleanly removes the AI Control Plane deployment.
#
# Usage:
#   bash scripts/uninstall.sh [--keep-volumes] [--force]
#
# Options:
#   --keep-volumes   Keep Docker volumes (preserve data)
#   --force          Skip confirmations
#
# This script will:
# 1. Stop all services
# 2. Remove containers
# 3. Remove the Docker network
# 4. Optionally remove volumes
# 5. Optionally backup/remove .env file
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
REPO_ROOT="$(dirname "$(readlink -f "$0")")/.."
ENV_FILE="$REPO_ROOT/.env"
KEEP_VOLUMES=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  ⚠️  AI Control Plane - Uninstall                      ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check .env exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${YELLOW}Note: No .env file found. System may not be fully deployed.${NC}"
    echo ""
fi

# Confirm uninstall
if [[ "$FORCE" != true ]]; then
    echo "This will:"
    echo "  1. Stop all AI Control Plane services"
    echo "  2. Remove Docker containers"
    echo "  3. Remove Docker network"
    if [[ "$KEEP_VOLUMES" != true ]]; then
        echo "  4. Remove all data volumes (⚠️ DESTRUCTIVE)"
        echo "  5. Backup .env file (optional)"
    else
        echo "  4. Keep data volumes (data preserved)"
        echo "  5. Backup .env file (optional)"
    fi
    echo ""
    
    read -p "Are you sure? (type 'uninstall' to confirm): " confirm
    if [[ "$confirm" != "uninstall" ]]; then
        echo -e "${YELLOW}Cancelled.${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${YELLOW}Starting uninstallation...${NC}"
echo ""

cd "$REPO_ROOT"

# Step 1: Stop services
echo -e "${YELLOW}[1/4] Stopping services...${NC}"
if docker compose ps | grep -q "infra"; then
    docker compose down
    echo -e "${GREEN}✓ Services stopped${NC}"
else
    echo -e "${YELLOW}⚠ No running services found${NC}"
fi

echo ""

# Step 2: Remove volumes
if [[ "$KEEP_VOLUMES" != true ]]; then
    echo -e "${YELLOW}[2/4] Removing data volumes...${NC}"
    
    # List volumes to be removed
    volumes=$(docker volume ls -q | grep "infra" || echo "")
    if [[ -n "$volumes" ]]; then
        echo "Volumes to be removed:"
        echo "$volumes" | sed 's/^/  - /'
        echo ""
        
        # Remove volumes
        docker volume rm $(docker volume ls -q | grep "infra") 2>/dev/null || true
        echo -e "${GREEN}✓ Volumes removed${NC}"
    else
        echo -e "${YELLOW}⚠ No volumes found${NC}"
    fi
else
    echo -e "${YELLOW}[2/4] Keeping data volumes${NC}"
    echo "  Your data is preserved in:"
    echo "    - prometheus_data (metrics history)"
    echo "    - grafana_data (dashboards & settings)"
    echo "    - ollama_data (cached models)"
    echo ""
    echo "  To remove manually later:"
    echo "    docker volume rm infra_prometheus_data"
    echo "    docker volume rm infra_grafana_data"
    echo "    docker volume rm infra_ollama_data"
    echo ""
fi

echo ""

# Step 3: Remove network
echo -e "${YELLOW}[3/4] Cleaning up Docker network...${NC}"
if docker network ls | grep -q "infra"; then
    docker network rm infra 2>/dev/null || true
    echo -e "${GREEN}✓ Network removed${NC}"
else
    echo -e "${YELLOW}⚠ Network not found${NC}"
fi

echo ""

# Step 4: Backup .env
echo -e "${YELLOW}[4/4] Handling .env file...${NC}"
if [[ -f "$ENV_FILE" ]]; then
    backup_file="$ENV_FILE.backup.$(date +%s)"
    cp "$ENV_FILE" "$backup_file"
    echo -e "${GREEN}✓ Configuration backed up to: $backup_file${NC}"
    
    # Ask to remove .env
    if [[ "$FORCE" != true ]]; then
        read -p "  Remove .env file? (y/n, default: n): " remove_env
        if [[ "$remove_env" == "y" || "$remove_env" == "Y" ]]; then
            rm "$ENV_FILE"
            echo -e "${GREEN}✓ .env file removed${NC}"
        else
            echo "  .env file kept (contains sensitive data)"
            echo "  ⚠️  Remember to delete it manually if sharing this directory"
        fi
    fi
else
    echo -e "${YELLOW}⚠ No .env file found${NC}"
fi

echo ""
echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  ✓ AI Control Plane has been uninstalled              ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Show remaining cleanup options
echo -e "${YELLOW}Optional cleanup:${NC}"
echo ""
echo "  Remove this repository:"
echo "    cd .. && rm -rf gururajseethur-infra"
echo ""
echo "  Clean up Docker completely:"
echo "    docker system prune -a"
echo ""
echo "  If Cloudflare Tunnel is still running:"
echo "    cloudflared tunnel delete ai-control-plane"
echo ""

# Summary
echo -e "${YELLOW}Summary:${NC}"
if [[ "$KEEP_VOLUMES" == true ]]; then
    echo "  ✓ Services: Stopped"
    echo "  ✓ Containers: Removed"
    echo "  ✓ Network: Removed"
    echo "  ✓ Volumes: Kept (data preserved)"
else
    echo "  ✓ Services: Stopped"
    echo "  ✓ Containers: Removed"
    echo "  ✓ Network: Removed"
    echo "  ✓ Volumes: Removed (data deleted)"
fi

if [[ -f "$backup_file" ]]; then
    echo "  ✓ Configuration: Backed up"
fi

echo ""
echo "Uninstall complete! 🗑️"
echo ""
