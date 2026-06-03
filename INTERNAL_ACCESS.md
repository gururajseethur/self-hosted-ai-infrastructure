# 🔐 Internal Access Guide - PHASE 3

## Overview

As of PHASE 3, **Grafana** and **Prometheus** are no longer publicly accessible. They are internal-only services, protecting sensitive operational data from unauthorized access.

**Key Changes:**
- ✅ Grafana (dashboard.domain, grafana.domain) — **REMOVED** public routes
- ✅ Prometheus (prometheus.domain) — **REMOVED** public routes
- ✅ Both services remain on internal Docker network (accessible to app backend)
- ✅ Admin access available via SSH tunnel or docker exec

---

## How to Access Internal Dashboards

### Option 1: SSH Tunnel (Recommended for Remote Access)

**For Grafana Dashboard:**
```bash
ssh -L 3000:localhost:3000 user@your-server.com
```
Then open in browser: `http://localhost:3000`

**Credentials:**
- Username: `admin`
- Password: Check your `.env` file (`GRAFANA_ADMIN_PASSWORD`)

**For Prometheus:**
```bash
ssh -L 9090:localhost:9090 user@your-server.com
```
Then open in browser: `http://localhost:9090`

---

### Option 2: Docker Exec (Direct Access on Server)

**Access Grafana directly:**
```bash
# Get the Grafana password from .env
grep GRAFANA_ADMIN_PASSWORD .env

# Open your browser to the container's health endpoint
docker compose exec grafana curl http://localhost:3000/api/health

# Or proxy through a running container
docker compose exec -it grafana-debugger bash
# Then from inside: curl http://grafana:3000
```

**Access Prometheus directly:**
```bash
docker compose exec prometheus curl http://localhost:9090/-/healthy
```

---

### Option 3: Port Forward via Docker (Quick Testing)

**Temporary Grafana access:**
```bash
docker compose port grafana 3000
# Note the port number, then:
docker compose exec -it grafana port-forward 3000
```

---

## App Backend Integration

The **AI Control Plane app** (backend) can still access Grafana and Prometheus internally:

```python
# In app/backend/main.py
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

# Query metrics via the service name
async def get_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "task:ollama_requests_total:rate5m"}
        )
        return response.json()
```

No changes needed—the app continues to work as before.

---

## Security Benefits

| Aspect | Before PHASE 3 | After PHASE 3 |
|--------|---|---|
| **Grafana Public** | ✗ Completely exposed, no auth | ✓ Internal-only, encrypted tunnel required |
| **Prometheus Public** | ⚠ Behind basic auth | ✓ Internal-only, no internet exposure |
| **Attack Surface** | All operational data visible | Minimal—only app backend queries metrics |
| **Compliance** | Potential data leakage | Secure by default |

---

## Admin Operations

### View Logs
```bash
# All services
docker compose logs -f --tail=50

# Specific service
docker compose logs grafana -f
docker compose logs prometheus -f
```

### Restart Services
```bash
docker compose restart grafana
docker compose restart prometheus
```

### Update Admin Password (Grafana)

**Method 1: Edit .env and restart**
```bash
nano .env
# Update: GRAFANA_ADMIN_PASSWORD=<new-password>
docker compose restart grafana
```

**Method 2: Via Grafana API**
```bash
# Get inside Grafana container
docker compose exec grafana bash

# Use grafana-cli
grafana-cli admin reset-admin-password newpassword
```

### Export Dashboards

```bash
# Backup all Grafana data
docker compose exec grafana grafana-cli plugin ls

# Or backup the volume
docker volume inspect grafana_data
# Backup path: /var/lib/docker/volumes/infra_grafana_data/_data
```

---

## Troubleshooting

**Q: I get "Connection refused" when trying to access Grafana via SSH tunnel**
- Check SSH tunnel is running: `lsof -i :3000`
- Verify Grafana container is running: `docker compose ps grafana`
- Check Docker network: `docker network inspect infra`

**Q: SSH tunnel works but Grafana shows "Not Found"**
- Grafana root URL is now `http://localhost:3000` (not the domain)
- Refresh your browser

**Q: I need to expose Grafana publicly again (e.g., for a demo)**
- Edit `docker-compose.yml`
- Add back the Traefik labels for Grafana
- Run: `docker compose restart grafana`
- Consider adding basic auth middleware

---

## Future: Internal Monitoring Dashboard

In a future update, we can add:
- ✨ Internal admin dashboard built into the AI Control Plane app
- ✨ Private metrics API endpoint (e.g., `/api/admin/metrics`)
- ✨ Request/error/latency visualizations
- ✨ Alerting configuration UI

This would eliminate the need for separate Grafana access entirely.

---

## Accessing Prometheus API Directly

If you need raw metrics data:

```bash
# Via SSH tunnel (3000 -> 9090 if you set it up)
curl http://localhost:9090/api/v1/query?query=ollama_requests_total

# Or from within the Docker network
docker compose exec -T app curl http://prometheus:9090/api/v1/query?query=ollama_up
```

---

## Summary

- ✅ **Grafana & Prometheus are now internal-only**
- ✅ **SSH tunnel** is the recommended way to access them remotely
- ✅ **docker exec** for quick access when logged into the server
- ✅ **App backend continues to work** without any changes
- ✅ **Much more secure** against unauthorized access

For more details, see [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md).
