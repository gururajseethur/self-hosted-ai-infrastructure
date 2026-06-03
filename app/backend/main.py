"""
AI Control Plane - Backend API

A FastAPI application that provides a unified interface to the AI infrastructure.

Customer-facing endpoints:
- /api/chat - AI chat interface
- /api/health - System health status
- /api/usage - Real-time metrics and usage statistics

Architecture:
- FastAPI for HTTP API
- Requests to ollama-proxy for AI interactions (transparent to customer)
- Prometheus HTTP API queries for metrics (hidden from customer)
- All responses are simplified and customer-friendly
"""

import os
import json
import logging
import httpx
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_PROXY_URL = os.getenv('OLLAMA_PROXY_URL', 'http://ollama-proxy:11435')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
API_PORT = int(os.getenv('API_PORT', 8000))

# FastAPI app
app = FastAPI(
    title="AI Control Plane",
    description="One-click AI infrastructure management",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

# ============================================
# Request/Response Models
# ============================================

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o-mini"


class ChatResponse(BaseModel):
    response: str
    model: str
    duration_ms: float


class HealthStatus(BaseModel):
    status: str  # "healthy", "degraded", "error"
    ollama: bool
    prometheus: bool
    exporter: bool
    message: str


class UsageStats(BaseModel):
    requests_per_second: float
    active_requests: int
    latency_p95_ms: float
    total_requests: int
    error_rate: float


# ============================================
# Helper Functions
# ============================================

async def query_prometheus(query: str) -> Optional[dict]:
    """
    Query Prometheus HTTP API and return result.
    
    Args:
        query: PromQL query string
    
    Returns:
        Query result or None if error
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{PROMETHEUS_URL}/api/v1/query',
                params={'query': query},
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data.get('data')
            return None
    except Exception as e:
        logger.error(f"Prometheus query failed: {e}")
        return None


async def check_ollama_health() -> bool:
    """Check if Ollama proxy is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{OLLAMA_PROXY_URL}/health',
                timeout=2.0
            )
            return response.status_code == 200
    except Exception:
        return False


async def check_prometheus_health() -> bool:
    """Check if Prometheus is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{PROMETHEUS_URL}/-/healthy',
                timeout=2.0
            )
            return response.status_code == 200
    except Exception:
        return False


async def check_exporter_health() -> bool:
    """Check if Ollama exporter is healthy."""
    try:
        data = await query_prometheus('ollama_up')
        if data and data.get('result'):
            value = float(data['result'][0]['value'][1])
            return value == 1.0
        return False
    except Exception:
        return False


def extract_prometheus_value(result: dict) -> Optional[float]:
    """Extract numeric value from Prometheus query result."""
    try:
        if result and result.get('result'):
            results = result.get('result', [])
            if results:
                return float(results[0]['value'][1])
        return None
    except Exception:
        return None


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint - product info."""
    return {
        "name": "AI Control Plane",
        "version": "1.0.0",
        "api": "/api",
        "ui": "/"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AI via Ollama.
    
    Forwards to ollama-proxy and returns response.
    Metrics are automatically recorded by the proxy.
    """
    import time
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{OLLAMA_PROXY_URL}/api/generate',
                json={
                    'model': request.model,
                    'prompt': request.prompt,
                    'stream': False
                },
                timeout=120.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Ollama error: {response.text}"
                )
            
            data = response.json()
            duration_ms = (time.time() - start_time) * 1000
            
            return ChatResponse(
                response=data.get('response', ''),
                model=request.model,
                duration_ms=duration_ms
            )
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")


@app.get("/api/health", response_model=HealthStatus)
async def health():
    """
    Health check endpoint.
    
    Returns status of all backend services.
    Simple green/red for customer dashboard.
    """
    ollama_ok = await check_ollama_health()
    prometheus_ok = await check_prometheus_health()
    exporter_ok = await check_exporter_health()
    
    all_ok = ollama_ok and prometheus_ok and exporter_ok
    
    if all_ok:
        status = "healthy"
        message = "All systems operational"
    elif ollama_ok and prometheus_ok:
        status = "degraded"
        message = "Metric exporter offline (AI still works)"
    else:
        status = "error"
        message = "Critical services offline"
    
    return HealthStatus(
        status=status,
        ollama=ollama_ok,
        prometheus=prometheus_ok,
        exporter=exporter_ok,
        message=message
    )


@app.get("/api/usage", response_model=UsageStats)
async def usage():
    """
    Real-time usage and performance metrics.
    
    Queries Prometheus and formats for customer display.
    If Prometheus is down, returns sensible defaults.
    """
    
    # Query requests per second (last 5 minutes)
    rps_data = await query_prometheus('sum(rate(ollama_requests_total[5m]))')
    requests_per_second = extract_prometheus_value(rps_data) or 0.0
    
    # Query active requests
    active_data = await query_prometheus('sum(ollama_requests_in_flight)')
    active_requests = int(extract_prometheus_value(active_data) or 0)
    
    # Query total requests
    total_data = await query_prometheus('sum(ollama_requests_total)')
    total_requests = int(extract_prometheus_value(total_data) or 0)
    
    # Query error rate (5 minutes)
    error_query = 'sum(rate(ollama_requests_total{status="error"}[5m])) / ignoring(status) group_left() sum(rate(ollama_requests_total[5m]))'
    error_data = await query_prometheus(error_query)
    error_rate = (extract_prometheus_value(error_data) or 0.0) * 100  # Convert to percentage
    
    # Query p95 latency (all models)
    p95_query = 'histogram_quantile(0.95, sum(rate(ollama_request_duration_seconds_bucket[5m])) by (le))'
    p95_data = await query_prometheus(p95_query)
    latency_p95_ms = (extract_prometheus_value(p95_data) or 0.0) * 1000  # Convert to ms
    
    return UsageStats(
        requests_per_second=round(requests_per_second, 2),
        active_requests=active_requests,
        latency_p95_ms=round(latency_p95_ms, 0),
        total_requests=total_requests,
        error_rate=round(error_rate, 1)
    )


@app.get("/api/models")
async def list_models():
    """
    List available AI models from Ollama.
    
    Forwards to ollama-proxy /api/tags endpoint.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{OLLAMA_PROXY_URL}/api/tags',
                timeout=5.0
            )
            
            if response.status_code != 200:
                return {"models": []}
            
            data = response.json()
            models = [m.get('name') for m in data.get('models', [])]
            
            return {
                "models": models,
                "count": len(models)
            }
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {"models": [], "count": 0}


@app.get("/admin/dashboard.html")
async def admin_dashboard():
    """
    Internal admin dashboard.
    
    Shows system metrics, health status, and operational data.
    Access via: http://localhost:8000/admin/dashboard.html
    Or through Traefik: https://app.domain/admin/dashboard.html
    
    Note: This is for internal operators only. Consider adding authentication.
    """
    from fastapi.responses import HTMLResponse
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>AI Control Plane - Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #eee;
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            header {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            h1 {
                font-size: 28px;
                margin-bottom: 5px;
                color: #4bf;
            }
            
            .subtitle {
                font-size: 14px;
                color: #aaa;
            }
            
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin-top: 10px;
            }
            
            .status-healthy { background: rgba(76, 175, 80, 0.3); border: 1px solid #4caf50; color: #81c784; }
            .status-degraded { background: rgba(255, 193, 7, 0.3); border: 1px solid #ffc107; color: #ffd54f; }
            .status-error { background: rgba(244, 67, 54, 0.3); border: 1px solid #f44336; color: #ef5350; }
            
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .card {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                padding: 20px;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.1);
                transition: all 0.3s ease;
            }
            
            .card:hover {
                background: rgba(255,255,255,0.08);
                border-color: rgba(255,255,255,0.2);
            }
            
            .card h2 {
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #aaa;
                margin-bottom: 15px;
            }
            
            .metric {
                font-size: 32px;
                font-weight: bold;
                color: #4bf;
                margin-bottom: 5px;
            }
            
            .metric-label {
                font-size: 12px;
                color: #777;
            }
            
            .metric-small {
                font-size: 18px;
                color: #81c784;
            }
            
            .health-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            
            .health-row:last-child {
                border-bottom: none;
            }
            
            .health-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            
            .health-indicator.ok { background: #4caf50; }
            .health-indicator.error { background: #f44336; }
            
            .refresh-btn {
                background: rgba(75, 192, 255, 0.2);
                border: 1px solid #4bf;
                color: #4bf;
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.3s;
            }
            
            .refresh-btn:hover {
                background: rgba(75, 192, 255, 0.3);
            }
            
            .footer {
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }
            
            .loading { opacity: 0.6; }
            .error { color: #ef5350; }
            .success { color: #81c784; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🎛️ AI Control Plane Admin Dashboard</h1>
                <p class="subtitle">Real-time system metrics and health status</p>
                <div id="systemStatus" class="status-badge status-healthy">● LOADING</div>
            </header>
            
            <div class="grid">
                <div class="card">
                    <h2>System Health</h2>
                    <div id="healthStatus">
                        <div class="loading">Loading...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Active Requests</h2>
                    <div class="metric" id="activeRequests">-</div>
                    <div class="metric-label">Currently processing</div>
                </div>
                
                <div class="card">
                    <h2>Requests/Sec</h2>
                    <div class="metric" id="requestsPerSecond">-</div>
                    <div class="metric-label">Last 5 minutes</div>
                </div>
                
                <div class="card">
                    <h2>P95 Latency</h2>
                    <div class="metric metric-small" id="latencyP95">-</div>
                    <div class="metric-label">milliseconds</div>
                </div>
                
                <div class="card">
                    <h2>Total Requests</h2>
                    <div class="metric metric-small" id="totalRequests">-</div>
                    <div class="metric-label">All time</div>
                </div>
                
                <div class="card">
                    <h2>Error Rate</h2>
                    <div class="metric metric-small" id="errorRate">-</div>
                    <div class="metric-label">Last 5 minutes</div>
                </div>
                
                <div class="card" style="grid-column: span 3;">
                    <h2>Service Status</h2>
                    <div id="serviceStatus">
                        <div class="loading">Loading...</div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <button class="refresh-btn" onclick="refreshMetrics()">🔄 Refresh Now</button>
                &nbsp; | &nbsp;
                Last updated: <span id="lastUpdate">-</span>
                &nbsp; | &nbsp;
                <a href="/" style="color: #4bf; text-decoration: none;">← Back to App</a>
            </div>
        </div>
        
        <script>
            async function refreshMetrics() {
                try {
                    const [health, usage] = await Promise.all([
                        fetch('/api/health').then(r => r.json()),
                        fetch('/api/usage').then(r => r.json())
                    ]);
                    
                    // Update system status
                    const statusEl = document.getElementById('systemStatus');
                    statusEl.textContent = health.status.toUpperCase();
                    statusEl.className = `status-badge status-${health.status}`;
                    
                    // Update health status details
                    document.getElementById('healthStatus').innerHTML = `
                        <div class="health-row">
                            <span><span class="health-indicator ${health.ollama ? 'ok' : 'error'}"></span>Ollama</span>
                            <span>${health.ollama ? '✓' : '✗'}</span>
                        </div>
                        <div class="health-row">
                            <span><span class="health-indicator ${health.prometheus ? 'ok' : 'error'}"></span>Prometheus</span>
                            <span>${health.prometheus ? '✓' : '✗'}</span>
                        </div>
                        <div class="health-row">
                            <span><span class="health-indicator ${health.exporter ? 'ok' : 'error'}"></span>Exporter</span>
                            <span>${health.exporter ? '✓' : '✗'}</span>
                        </div>
                        <div class="health-row" style="border-bottom: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05);">
                            <strong style="color: #999;">${health.message}</strong>
                        </div>
                    `;
                    
                    // Update metrics
                    document.getElementById('activeRequests').textContent = usage.active_requests;
                    document.getElementById('requestsPerSecond').textContent = usage.requests_per_second;
                    document.getElementById('latencyP95').textContent = usage.latency_p95_ms.toFixed(0) + ' ms';
                    document.getElementById('totalRequests').textContent = usage.total_requests;
                    document.getElementById('errorRate').textContent = usage.error_rate.toFixed(1) + '%';
                    
                    // Update timestamp
                    const now = new Date();
                    document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
                    
                } catch (error) {
                    console.error('Dashboard update failed:', error);
                    document.getElementById('systemStatus').className = 'status-badge status-error';
                    document.getElementById('systemStatus').textContent = '✗ ERROR';
                }
            }
            
            // Initial load
            refreshMetrics();
            
            // Auto-refresh every 3 seconds
            setInterval(refreshMetrics, 3000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


# ============================================
# Startup & Shutdown
# ============================================

@app.on_event("startup")
async def startup():
    """Log startup info."""
    logger.info("AI Control Plane Backend starting")
    logger.info(f"Ollama Proxy: {OLLAMA_PROXY_URL}")
    logger.info(f"Prometheus: {PROMETHEUS_URL}")


@app.on_event("shutdown")
async def shutdown():
    """Log shutdown."""
    logger.info("AI Control Plane Backend shutting down")


# ============================================
# Main
# ============================================

if __name__ == '__main__':
    import uvicorn
    
    logger.info(f"Starting API server on 0.0.0.0:{API_PORT}")
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=API_PORT,
        log_level='info'
    )
