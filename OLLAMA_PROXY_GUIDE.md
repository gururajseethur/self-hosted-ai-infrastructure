# Ollama Proxy Integration Guide

The Ollama Proxy automatically instruments all requests to Ollama, capturing metrics without requiring any changes to your application code.

## Quick Integration

### Before (No Metrics)
```python
import requests

response = requests.post('http://ollama:11434/api/generate', json={
    'model': 'gpt-4o-mini',
    'prompt': 'hello world'
})
```

### After (With Proxy Auto-Metrics)
```python
import requests

response = requests.post('http://ollama-proxy:11435/api/generate', json={
    'model': 'gpt-4o-mini',
    'prompt': 'hello world'
})
# Metrics are automatically recorded!
```

That's it. No code changes beyond the endpoint URL.

---

## How It Works Under the Hood

1. **Request arrives** at proxy (port 11435)
2. **Model name extracted** from JSON body (looks for `"model"` key)
3. **"start" event sent** to exporter: `POST /observe {"model":"...", "event":"start"}`
4. **Request forwarded** to Ollama (port 11434) with full streaming support
5. **Duration measured** and "done" event sent: `POST /observe {"model":"...", "event":"done", "duration":0.42, "success":true}`
6. **Response streamed** back to client (transparent, same as direct Ollama)

---

## Integration Examples

### Python + requests
```python
import requests
import json

BASE_URL = 'http://ollama-proxy:11435'

# Generate endpoint
response = requests.post(f'{BASE_URL}/api/generate', json={
    'model': 'gpt-4o-mini',
    'prompt': 'What is the capital of France?',
    'stream': True
})

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        print(data.get('response', ''), end='', flush=True)
```

### Node.js + fetch
```javascript
const baseUrl = 'http://ollama-proxy:11435';

const response = await fetch(`${baseUrl}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        model: 'gpt-4o-mini',
        prompt: 'Hello, world!'
    })
});

const data = await response.json();
console.log(data);
```

### cURL
```bash
curl -X POST http://ollama-proxy:11435/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "prompt": "Tell me a joke"
  }'
```

### Docker Container
If your app is running in another Docker container on the same `infra` network:

```bash
# Inside your app container
curl -X POST http://ollama-proxy:11435/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","prompt":"hello"}'
```

### Via Cloudflare Tunnel (External)
```bash
# From outside your network
curl -X POST https://ollama-proxy.gururajseethur.in/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)" \
  -d '{"model":"gpt-4o-mini","prompt":"hello"}'
```

---

## Metrics Available After Proxy Use

Once you're using the proxy, these metrics are automatically available in Prometheus and Grafana:

### Gauge Metrics
- `ollama_up` — 1 if Ollama backend is reachable, 0 otherwise
- `ollama_models_loaded` — number of models currently loaded in Ollama
- `ollama_requests_in_flight` — current number of requests being processed

### Counter Metrics
- `ollama_requests_total{model="...", status="success|error"}` — cumulative requests per model and status

### Histogram Metrics
- `ollama_request_duration_seconds{model="..."}` — request latency (includes buckets for percentiles)

### Example Prometheus Queries
```promql
# Requests per second per model (last 5 minutes)
rate(ollama_requests_total[5m]) by (model)

# Error rate (last 5 minutes)
rate(ollama_requests_total{status="error"}[5m]) / ignoring(status) group_left
rate(ollama_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(ollama_request_duration_seconds_bucket[5m]))

# Active requests now
ollama_requests_in_flight
```

### Example Grafana Dashboard
See `config/grafana/dashboards/ollama-metrics.json` for a pre-built dashboard with:
- Requests per model (rate)
- Active requests (gauge)
- Error rate (%)
- Latency P95 (histogram)

---

## Model Name Extraction

The proxy looks for the `"model"` key in your request JSON. This works with all standard Ollama endpoints:

### Supported Endpoints
- `/api/generate` — uses `"model"` ✓
- `/api/embeddings` — uses `"model"` ✓
- `/api/chat` — uses `"model"` ✓
- `/api/pull` — uses `"name"` (fallback) ✓
- `/api/list` — no model (labeled as `"unknown"`) ✓

### Custom Requests
If your request uses a different field, the proxy will label it `"unknown"`:

```python
# This will be labeled "unknown" in metrics
response = requests.post(f'{BASE_URL}/custom-endpoint', json={
    'llm_name': 'gpt-4o-mini',  # Not recognized
    'prompt': 'hello'
})
```

To fix, ensure your requests use the standard `"model"` key.

---

## Error Handling

The proxy gracefully handles errors and always forwards them to the client:

### Ollama Unavailable
```
Client → Proxy: request
Proxy → Ollama: **connection error**
Proxy → Client: HTTP 503 (Service Unavailable)
Proxy → Exporter: event="done", success=false
Metrics recorded with error status.
```

### Exporter Unavailable
```
Client → Proxy: request
Proxy → Ollama: **success**
Proxy → Exporter: **connection error** (logged, ignored)
Proxy → Client: HTTP 200 (response forwarded)
Metrics NOT recorded (exporter down).
```

The key design: **Exporter failures don't break your app**. Metrics are best-effort and optional.

---

## Configuration

Proxy behavior is controlled via environment variables (in `docker-compose.yml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BACKEND_URL` | `http://ollama:11434` | Ollama service address |
| `EXPORTER_URL` | `http://ollama-exporter:9091` | Exporter address |
| `PROXY_PORT` | `11435` | Port proxy listens on |
| `REQUEST_TIMEOUT` | `60` | Request timeout in seconds |

To customize, edit `docker-compose.yml` before deploying:

```yaml
ollama-proxy:
  environment:
    - OLLAMA_BACKEND_URL=http://custom-ollama:11434
    - EXPORTER_URL=http://custom-exporter:9091
    - PROXY_PORT=11435
    - REQUEST_TIMEOUT=120
```

Then redeploy:
```bash
./scripts/deploy.sh
```

---

## Troubleshooting

### Proxy Not Responding
```bash
# Check if container is running
docker ps | grep ollama-proxy

# View logs
docker logs ollama-proxy

# Test endpoint
docker exec ollama-proxy curl http://localhost:11435/health
```

### Metrics Not Appearing
1. Confirm proxy is in use (not direct Ollama)
2. Check exporter is running: `docker ps | grep ollama-exporter`
3. Verify Prometheus scraping: `http://prometheus:9090/targets`
4. Wait 10 seconds (default scrape interval)

### High Latency
- Default gunicorn: 4 workers. Increase in Dockerfile if needed.
- Check Ollama backend performance separately.
- Proxy overhead is ~1-5ms per request.

### Custom Model Names Not Recognized
- Ensure request JSON has `"model"` key (standard Ollama API)
- If not, metrics will show `"unknown"`
- File a GitHub issue if endpoint uses non-standard field

---

## Production Deployment

### Recommended Setup
1. Deploy via `./scripts/deploy.sh`
2. Configure Cloudflare Tunnel auth for proxy endpoint
3. Monitor via Grafana dashboard
4. Set alerts on error rates (Prometheus AlertManager)

### Scaling
For high request volume:
1. Increase Gunicorn workers in `Dockerfile`: `gunicorn -w 8 ...`
2. Or upgrade to async framework (Quart)
3. Or run multiple proxy instances (load-balanced)

### Security
- Proxy runs inside Docker network (no direct host exposure)
- All external access via Cloudflare Tunnel (encrypted)
- Basic auth on tunnel endpoints (Traefik middleware)
- No secrets stored in proxy code

---

## FAQ

**Q: Do I need to modify my app to use the proxy?**
A: No. Just change the Ollama endpoint URL from `ollama:11434` to `ollama-proxy:11435`.

**Q: What if the exporter crashes?**
A: Proxy still works. Metrics won't be recorded, but your app isn't affected.

**Q: Can proxy handle streaming requests?**
A: Yes. Both request and response streaming are fully supported.

**Q: Is there performance overhead?**
A: ~1-5ms per request (network roundtrip to exporter). Negligible for most workloads.

**Q: Can I use proxy in production?**
A: Yes. It's designed for production use with proper error handling and logging.

**Q: How do I disable the proxy?**
A: Switch back to direct Ollama: `ollama:11434`. Metrics will no longer be automatic.

---

## Support

For issues or questions:
1. Check logs: `docker logs ollama-proxy`
2. Test manually: `curl http://ollama-proxy:11435/health`
3. File GitHub issue with logs and steps to reproduce
