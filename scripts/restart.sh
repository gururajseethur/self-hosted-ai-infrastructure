#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "🔄 Restarting all services..."
docker-compose restart

echo ""
echo "⏳ Waiting for services to stabilize (30s)..."
sleep 30

echo ""
echo "✅ Services restarted"
echo "   View logs: docker-compose logs -f"
