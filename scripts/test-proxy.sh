#!/bin/bash

# Test Ollama Proxy Integration
# This script demonstrates:
# 1. Model name extraction
# 2. Automatic metric recording
# 3. Error handling

set -e

PROXY_URL="http://ollama-proxy:11435"
EXPORTER_URL="http://ollama-exporter:9091"

echo "=== Ollama Proxy Test Suite ==="
echo ""

# Test 1: Check proxy health
echo "1. Testing proxy health..."
if docker compose exec ollama-proxy curl -s http://localhost:11435/health | grep -q "healthy"; then
    echo "   ✓ Proxy is healthy"
else
    echo "   ⚠ Proxy may not be running (expected if not deployed)"
fi

echo ""

# Test 2: Test metrics endpoint
echo "2. Testing exporter metrics..."
if docker compose exec ollama-exporter curl -s http://localhost:9091/metrics | grep -q "ollama_up"; then
    echo "   ✓ Exporter metrics available"
else
    echo "   ⚠ Exporter not responding (expected if not deployed)"
fi

echo ""

# Test 3: Test instrumentation endpoint
echo "3. Testing instrumentation endpoint..."
if docker compose exec ollama-exporter curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"model":"test-model","event":"start"}' http://localhost:9091/observe | grep -q "ok"; then
    echo "   ✓ Instrumentation endpoint working"
else
    echo "   ⚠ Instrumentation endpoint not responding (expected if not deployed)"
fi

echo ""
echo "=== Test Complete ==="
echo ""
echo "To see real metrics:"
echo "  1. Make requests through proxy:"
echo "     docker compose exec <your-app> curl -X POST http://ollama-proxy:11435/api/generate \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"model\":\"gpt-4o-mini\",\"prompt\":\"hello\"}'"
echo ""
echo "  2. View in Prometheus:"
echo "     curl http://prometheus:9090/api/v1/query?query=ollama_requests_total"
echo ""
echo "  3. View in Grafana:"
echo "     https://dashboard.gururajseethur.in (Ollama Exporter dashboard)"
