"""
Ollama Prometheus Exporter
Exports metrics: models loaded, active requests, API health
MVP for monitoring Ollama instances
"""

import os
import time
import requests
import logging
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from threading import Thread, Lock
from flask import Flask, request, Response, jsonify

# Configuration
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
METRICS_PORT = int(os.getenv('METRICS_PORT', 9091))
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', 10))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
# Using labels where appropriate. 'status' is 'success' or 'error'.
registry = CollectorRegistry()

ollama_models_loaded = Gauge('ollama_models_loaded', 'Number of models currently loaded', registry=registry)
ollama_up = Gauge('ollama_up', 'Ollama API up (1=up, 0=down)', registry=registry)
ollama_requests_in_flight = Gauge('ollama_requests_in_flight', 'Number of in-flight requests', registry=registry)
ollama_request_duration_seconds = Histogram(
    'ollama_request_duration_seconds',
    'Duration of Ollama requests in seconds',
    ['model'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    registry=registry
)
ollama_requests_total = Counter(
    'ollama_requests_total',
    'Total number of observed Ollama requests',
    ['model', 'status'],
    registry=registry
)

# Internal state for inference when Ollama does not expose request stats
inflight_lock = Lock()
inflight_by_model = {}

# Flask app for optional instrumentation hooks and /metrics
app = Flask(__name__)


@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics. We use generate_latest against our registry.

    Note: We intentionally serve metrics on the same HTTP interface as the
    instrumentation endpoint to keep the container network-only (no host ports).
    """
    resp = generate_latest(registry)
    return Response(resp, mimetype=CONTENT_TYPE_LATEST)


@app.route('/observe', methods=['POST'])
def observe():
    """Optional instrumentation endpoint for recording request lifecycle.

    Accepted JSON payloads:
      - {"model": "gpt-4o-mini", "event": "start"}
        increments in-flight counters.
      - {"model": "gpt-4o-mini", "event": "done", "duration": 0.23, "success": true}
        decrements in-flight and records duration + increments total.

    This endpoint is intentionally permissive and additive: if your app can
    emit these signals (best-effort), metrics will be accurate. If not,
    the exporter still attempts best-effort inference from Ollama API.
    """
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    model = str(payload.get('model', 'unknown'))
    event = payload.get('event')

    if not model or not event:
        return jsonify({"error": "model and event required"}), 400

    # Normalize
    model = model or 'unknown'
    event = event.lower()

    if event == 'start':
        with inflight_lock:
            inflight_by_model[model] = inflight_by_model.get(model, 0) + 1
            total_inflight = sum(inflight_by_model.values())
            ollama_requests_in_flight.set(total_inflight)
        return jsonify({"status": "ok", "in_flight": inflight_by_model.get(model)}), 202

    if event == 'done':
        duration = None
        try:
            duration = float(payload.get('duration')) if payload.get('duration') is not None else None
        except Exception:
            duration = None

        success = payload.get('success')
        status_label = 'success' if success is True or str(success).lower() == 'true' else 'error'

        # Update internal in-flight
        with inflight_lock:
            if inflight_by_model.get(model, 0) > 0:
                inflight_by_model[model] -= 1
            total_inflight = sum(inflight_by_model.values())
            ollama_requests_in_flight.set(total_inflight)

        # Record metrics
        ollama_requests_total.labels(model=model, status=status_label).inc()
        if duration is not None:
            try:
                ollama_request_duration_seconds.labels(model=model).observe(float(duration))
            except Exception:
                logger.exception('Failed to observe duration')

        return jsonify({"status": "recorded", "model": model}), 200

    return jsonify({"error": "unknown event"}), 400


def get_ollama_models():
    """Fetch list of loaded models from Ollama"""
    try:
        response = requests.get(f'{OLLAMA_API_URL}/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return len(models), [m.get('name', 'unknown') for m in models]
        return 0, []
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return 0, []

def check_ollama_health():
    """Check Ollama API health"""
    try:
        response = requests.get(f'{OLLAMA_API_URL}/api/tags', timeout=5)
        return 1 if response.status_code == 200 else 0
    except:
        return 0

def collect_metrics():
    """Collect metrics from Ollama"""
    while True:
        try:
            # Check health
            health = check_ollama_health()
            ollama_up.set(health)
            
            if health:
                # Get loaded models
                model_count, models = get_ollama_models()
                ollama_models_loaded.set(model_count)
                
                logger.info(f"Loaded models: {model_count} - {models}")
            # Try to infer active requests from Ollama API endpoints (best-effort).
            #
            # Assumptions & limitations:
            # - Ollama may not expose a requests/sessions endpoint; we attempt both
            #   and fallback to internal instrumentation counters if unavailable.
            # - If your application cannot POST to /observe, counts will be based
            #   on best-effort inference and may undercount/overcount depending
            #   on upstream Ollama behavior and API compatibility.
            # - This exporter is intentionally defensive: failures to query the
            #   Ollama API will not crash the exporter; we log and fallback.
            in_flight = None
            try:
                r = requests.get(f'{OLLAMA_API_URL}/api/requests', timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    # If the endpoint returns a list of requests, count them
                    if isinstance(data, list):
                        in_flight = len(data)
                    # If it's a dict with keys, try to infer
                    elif isinstance(data, dict):
                        # look for common keys
                        if 'in_progress' in data and isinstance(data['in_progress'], list):
                            in_flight = len(data['in_progress'])
                        elif 'requests' in data and isinstance(data['requests'], list):
                            in_flight = len(data['requests'])
            except Exception:
                # ignore and try sessions
                pass

            if in_flight is None:
                try:
                    r = requests.get(f'{OLLAMA_API_URL}/api/sessions', timeout=3)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, list):
                            in_flight = sum(1 for s in data if s.get('status') == 'in_progress') if isinstance(data, list) else None
                except Exception:
                    pass

            # Fallback to internal instrumentation if inference failed
            if in_flight is None:
                with inflight_lock:
                    in_flight = sum(inflight_by_model.values())

            # Update metric
            try:
                ollama_requests_in_flight.set(in_flight or 0)
            except Exception:
                logger.exception('Failed to set in-flight metric')
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        time.sleep(SCRAPE_INTERVAL)

def main():
    """Start metrics server and collection loop"""
    logger.info(f"Starting Ollama Exporter on port {METRICS_PORT}")
    logger.info(f"Ollama API URL: {OLLAMA_API_URL}")
    # Start metrics collection thread
    collector_thread = Thread(target=collect_metrics, daemon=True)
    collector_thread.start()

    # Start Flask app to serve /metrics and /observe on the configured port.
    # The Flask dev server is acceptable inside a container and we keep the
    # container network-only (docker-compose uses `expose`, not host ports).
    try:
        app.run(host='0.0.0.0', port=METRICS_PORT)
    except Exception:
        logger.exception('Flask server crashed')

if __name__ == '__main__':
    main()
