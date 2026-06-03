"""
Ollama Instrumentation Proxy

This lightweight proxy forwards all requests to the real Ollama service
and records metrics with the ollama-exporter for observability.

How it works:
1. Client sends request to http://ollama-proxy:11435
2. Proxy extracts model name from request JSON (if available)
3. Proxy sends "start" event to http://ollama-exporter:9091/observe
4. Proxy forwards request to http://ollama:11434
5. Proxy records "done" event with duration and success status
6. Proxy streams response back to client

Assumptions & limitations:
- Model name extraction assumes JSON body with "model" or "request" key
- If exporter is down, proxy still works (metrics not recorded, best-effort)
- Request/response are streamed or buffered depending on size
- Errors from Ollama are forwarded transparently to client
- Connection timeouts, body parsing errors are gracefully handled

Design note:
- We use Flask (threaded) for simplicity inside a container.
- For ultra-high throughput, consider async framework (FastAPI/Quart).
- Gunicorn wraps the app with multiple workers for concurrency.
"""

import os
import json
import time
import logging
import requests
from threading import Thread
from io import BytesIO
from flask import Flask, request, Response, stream_with_context

# Configuration
OLLAMA_BACKEND_URL = os.getenv('OLLAMA_BACKEND_URL', 'http://ollama:11434')
EXPORTER_URL = os.getenv('EXPORTER_URL', 'http://ollama-exporter:9091')
PROXY_PORT = int(os.getenv('PROXY_PORT', 11435))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 60))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


def extract_model_name(body_data: bytes) -> str:
    """
    Try to extract model name from request body JSON.
    
    Ollama API uses "model" key in /api/generate, /api/embeddings, etc.
    Some endpoints may use different keys. We try common patterns.
    
    Args:
        body_data: raw request body bytes
    
    Returns:
        model name string or "unknown" if not found
    """
    if not body_data:
        return "unknown"
    
    try:
        payload = json.loads(body_data.decode('utf-8'))
        
        # Try common keys
        for key in ['model', 'model_name', 'name']:
            if key in payload:
                value = payload[key]
                if isinstance(value, str):
                    return value or "unknown"
        
        # Fallback: return "unknown"
        return "unknown"
    except Exception as e:
        logger.debug(f"Failed to extract model: {e}")
        return "unknown"


def notify_exporter(model: str, event: str, duration: float = None, success: bool = None):
    """
    Send event to ollama-exporter for metric recording.
    
    This is best-effort: if the exporter is down, we log and continue.
    Client requests are never blocked by exporter failures.
    
    Args:
        model: model name
        event: "start" or "done"
        duration: request duration in seconds (for "done" events)
        success: True/False (for "done" events)
    """
    payload = {"model": model, "event": event}
    
    if event == "done":
        if duration is not None:
            payload["duration"] = duration
        if success is not None:
            payload["success"] = success
    
    try:
        respond = requests.post(
            f'{EXPORTER_URL}/observe',
            json=payload,
            timeout=2
        )
        if respond.status_code not in (200, 202):
            logger.warning(f"Exporter returned {respond.status_code} for {event} event")
    except Exception as e:
        logger.warning(f"Failed to notify exporter: {e}")
        # Do NOT raise; proxy continues regardless


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def proxy_all(path):
    """
    Universal proxy: forward all requests to Ollama backend.
    
    Process:
    1. Buffer request body
    2. Extract model name if present
    3. Notify exporter: "start"
    4. Forward to Ollama with streaming response
    5. Record duration and success
    6. Notify exporter: "done"
    7. Return response
    """
    
    # Build target URL
    target_path = f'/{path}' if path else '/'
    target_url = f'{OLLAMA_BACKEND_URL}{target_path}'
    
    # Preserve query string
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'
    
    logger.info(f"Proxying {request.method} {target_path}")
    
    # Read request body (may be empty for GET)
    try:
        body = request.get_data()
    except Exception as e:
        logger.error(f"Failed to read request body: {e}")
        return {"error": "bad request"}, 400
    
    # Extract model name
    model = extract_model_name(body)
    
    # Notify exporter: request started
    notify_exporter(model, "start")
    
    # Forward request to Ollama backend
    start_time = time.time()
    success = False
    response_status = 500
    
    try:
        # Prepare headers (pass through, but remove host)
        headers = {k: v for k, v in request.headers if k.lower() not in ('host', 'connection')}
        
        # Forward with timeout
        response = requests.request(
            method=request.method,
            url=target_url,
            data=body if body else None,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=True
        )
        
        response_status = response.status_code
        success = response_status < 400
        
        # Stream response back to client
        def generate():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Error streaming response: {e}")
                yield b''
        
        duration = time.time() - start_time
        
        # Notify exporter: request done
        notify_exporter(model, "done", duration=duration, success=success)
        
        return Response(
            stream_with_context(generate()),
            status=response_status,
            headers=dict(response.headers)
        )
    
    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        logger.error(f"Request timeout after {duration}s")
        notify_exporter(model, "done", duration=duration, success=False)
        return {"error": "upstream timeout"}, 504
    
    except requests.exceptions.ConnectionError as e:
        duration = time.time() - start_time
        logger.error(f"Connection error: {e}")
        notify_exporter(model, "done", duration=duration, success=False)
        return {"error": "upstream unavailable"}, 503
    
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"Unexpected error: {e}")
        notify_exporter(model, "done", duration=duration, success=False)
        return {"error": "proxy error"}, 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (for Docker/Kubernetes probes)."""
    try:
        # Check if backend is reachable
        resp = requests.get(f'{OLLAMA_BACKEND_URL}/api/tags', timeout=2)
        return {"status": "healthy", "backend": resp.status_code == 200}, 200
    except Exception:
        return {"status": "degraded", "backend": False}, 200


def main():
    """Start the proxy server."""
    logger.info(f"Starting Ollama Instrumentation Proxy on port {PROXY_PORT}")
    logger.info(f"Backend: {OLLAMA_BACKEND_URL}")
    logger.info(f"Exporter: {EXPORTER_URL}")
    
    # Run Flask app via gunicorn (called by Docker CMD)
    # For local development, uncomment:
    # app.run(host='0.0.0.0', port=PROXY_PORT, debug=False)


if __name__ == '__main__':
    main()
