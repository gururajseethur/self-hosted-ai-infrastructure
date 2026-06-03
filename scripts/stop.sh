#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛑 Stopping all services..."
cd "$REPO_ROOT"

docker-compose down

echo "✅ All services stopped and removed"
echo ""
echo "💾 Persistent data (volumes) preserved:"
echo "   - prometheus_data"
echo "   - grafana_data"
echo "   - ollama_data"
echo ""
echo "To destroy everything including data:"
echo "   docker-compose down -v"
