# 📖 Operations Guide

**Daily, monthly, and emergency operations for the infra platform.**

---

## 🏃 Daily Operations

### Check System Health (Morning)
```bash
cd ~/gururajseethur-infra
./scripts/status.sh
```

**Look for:**
- All containers `Up`
- CPU < 80%
- Memory < 85%
- Cloudflared connected

### Check Dashboard (Visual)
```
https://dashboard.gururajseethur.in
→ Login
→ Review panels:
   - Ollama Health: Green (✓)
   - Models Loaded: > 0
   - CPU Usage: Normal
   - Memory Usage: Normal
```

### Monitoring for Alerts
Prometheus stores all metrics. Set up in Grafana:
```
Alerting → Alert Rules → Create Rule
Condition: cpu_usage > 80% for 5 minutes
Actions: Send to your email/Slack
```

---

## 📅 Weekly Operations

### Backup Prometheus Data
```bash
docker run --rm -v gururajseethur-infra_prometheus_data:/data \
  -v ~/backups:/backup \
  alpine tar czf /backup/prometheus-weekly-$(date +%Y%m%d).tar.gz -C /data .

# Verify backup
ls -lh ~/backups/
```

### Review Metrics & Trends
```
https://dashboard.gururajseethur.in
→ Set time range to "Last 7 days"
→ Look for:
   - Memory leaks (steadily climbing)
   - CPU spikes
   - Network anomalies
   - Ollama model unloading/reloading
```

### Clean Docker System
```bash
docker system prune -a --volumes
# Removes unused images, networks, dangling volumes
```

---

## 🔄 Update Operations

### Update Base Images
```bash
cd ~/gururajseethur-infra

# Pull latest versions
docker-compose pull

# Restart with new images
docker-compose up -d

# Verify
docker-compose ps
./scripts/status.sh
```

**Restart order (automatic):**
1. Traefik
2. Prometheus, Node Exporter, cAdvisor
3. Grafana
4. Cloudflared

### Update Configurations
```bash
# Edit config file
nano config/prometheus/prometheus.yml

# Apply
docker-compose restart prometheus

# Verify
docker logs prometheus | tail -20
```

### Rebuild Custom Images
```bash
# If you modify exporter/ollama/app.py
docker-compose build --no-cache ollama-exporter

# Restart
docker-compose restart ollama-exporter
```

---

## 🔐 Maintenance Operations

### Rotate Grafana Admin Password
```bash
# 1. Log into Grafana
https://dashboard.gururajseethur.in
→ Admin → Preferences → Change password

# 2. Update .env (for re-deploy)
nano .env
GRAFANA_ADMIN_PASSWORD=NewPasswordHere

# 3. No restart needed (already changed in DB)
```

### Rotate Traefik Basic Auth
```bash
# 1. Generate new password hash
htpasswd -c -b hash.txt admin NewPassword

# 2. Update
cat hash.txt
# Copy output

# 3. Edit config
nano config/traefik/dynamic.yml
# Replace users line with new hash

# 4. Apply
docker-compose restart traefik
```

### Renew Let's Encrypt Certificates (Auto)
- Traefik renews automatically 30 days before expiry
- No action needed
- Check logs: `docker logs traefik | grep acme`

---

## 🚨 Emergency Operations

### Service Down: Immediate Recovery
```bash
# 1. Identify failed service
docker-compose ps
# Look for "Exited" status

# 2. Check logs
docker-compose logs SERVICENAME | tail -50

# 3. Restart
docker-compose restart SERVICENAME

# 4. Monitor
docker logs -f SERVICENAME
```

### Disk Space Full
```bash
# 1. Check space
docker system df

# 2. Find large volumes
du -sh volumes/*

# 3. Archive old Prometheus data
# (Prometheus auto-cleans after 7 days by default)

# 4. Manual cleanup
docker system prune -a --volumes
```

### Tunnel Disconnected
```bash
# Signs: Cannot access dashboard from outside

# 1. Check tunnel status
docker logs cloudflared | tail -20

# 2. Restart tunnel
docker-compose restart cloudflared

# 3. Verify in Cloudflare dashboard
https://dash.cloudflare.com/
→ Zero Trust → Tunnels → Your Tunnel
→ Should show "Connected"

# 4. Wait 30-60s for DNS propag ation
```

### Prometheus OOM (Out of Memory)
```bash
# 1. Check memory
docker stats prometheus

# 2. Current retention: 7 days (default)
# To reduce: Edit .env, set PROMETHEUS_RETENTION=3d

# 3. Restart
docker-compose restart prometheus
```

### Ollama Not Responding
```bash
# 1. Check service
docker-compose ps ollama

# 2. Check logs
docker logs ollama

# 3. Restart
docker-compose restart ollama

# 4. Pre-load a model (if needed)
docker exec ollama ollama pull mistral

# 5. Verify exporter can reach it
docker logs ollama-exporter
```

---

## 🚀 Scaling Operations

### Add More Ollama Models
```bash
docker exec ollama ollama pull llama2
docker exec ollama ollama pull qwen:7b

# Verify
docker exec ollama ollama list

# Monitor in Grafana
dashboard.gururajseethur.in
→ "Ollama Models Loaded" card
```

### Monitor Remote Hosts (Future)
Add Node Exporters on other machines:

```bash
# On remote machine
docker run -d \
  --name node-exporter \
  -p 9100:9100 \
  prom/node-exporter:latest

# On control machine, edit prometheus.yml
  - job_name: 'remote-host-1'
    static_configs:
      - targets: ['192.168.1.100:9100']

docker-compose restart prometheus
```

### Multi-Datacenter Setup (Future)
- Deploy this entire stack in multiple regions
- Individual dashboards per region
- Central Prometheus federation (scrape other Prometheus instances)
- Grafana: Add multiple Prometheus datasources

---

## 📊 Advanced Monitoring

### Create Custom Alert Rules
```bash
# 1. Create alerts.rules.yml
cat > config/prometheus/alerts.rules.yml << 'EOF'
groups:
  - name: infra
    rules:
      - alert: HighCPUUsage
        expr: node_cpu_seconds_total > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"

      - alert: OllamaDown
        expr: ollama_api_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Ollama is unavailable"
EOF

# 2. Update prometheus.yml
cat >> config/prometheus/prometheus.yml << 'EOF'
rule_files:
  - /etc/prometheus/alerts.rules.yml
EOF

# 3. Update docker-compose.yml (mount alerts file)
# volumes:
#   - ./config/prometheus/alerts.rules.yml:/etc/prometheus/alerts.rules.yml:ro

# 4. Restart
docker-compose restart prometheus
```

### Query Metrics from Command Line
```bash
# Get Prometheus query results
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq .

# Calculate uptime
curl -s 'http://localhost:9090/api/v1/query?query=up{job="prometheus"}' | jq '.data.result[0].value[1]'
```

### Export Metrics for Analysis
```bash
# Snapshot Prometheus data for analysis
docker exec prometheus tar czf /prometheus/snapshot.tar.gz \
  -C /prometheus/LATEST --one-file-system .

# Extract locally
docker cp prometheus:/prometheus/snapshot.tar.gz ./
tar xzf snapshot.tar.gz
```

---

## 🔄 Disaster Recovery

### Full Restore from Backup
```bash
# 1. Stop services
docker-compose down

# 2. Remove old volume
docker volume rm gururajseethur-infra_prometheus_data

# 3. Create new volume
docker volume create gururajseethur-infra_prometheus_data

# 4. Restore backup
docker run --rm -v gururajseethur-infra_prometheus_data:/data \
  -v ~/backups:/backup \
  alpine tar xzf /backup/prometheus-weekly-20260205.tar.gz -C /data

# 5. Restart
docker-compose up -d

# 6. Verify
docker-compose ps
./scripts/status.sh
```

### Migrate to New Server
```bash
# On OLD server
docker volume export prometheus_data > prometheus.backup
docker volume export grafana_data > grafana.backup

# Transfer files to NEW server
scp prometheus.backup user@newserver:~/
scp grafana.backup user@newserver:~/
(also copy entire ./config directory)

# On NEW server
docker volume import prometheus_data prometheus.backup
docker volume import grafana_data grafana.backup

cd ~/gururajseethur-infra
cp .env.template .env
# Edit .env with new config
./scripts/deploy.sh
```

---

## 📈 Performance Tuning

### Prometheus Retention Optimization
```bash
# Current: 7 days (in .env)
# Trade-off: More retention = More disk

# For 30-days retention:
nano .env
PROMETHEUS_RETENTION=30d

docker-compose restart prometheus
# Will store ~30GB more data

# For 3-days retention (space-constrained):
PROMETHEUS_RETENTION=3d
```

### Grafana Performance
```bash
# Default refresh: 30s
# To reduce load: Dashboard → Settings → Refresh interval = 1m

# Disable unused panels
# Disable unused plugins in Settings
```

### Disable Unused Exporters
```bash
# Edit docker-compose.yml, comment out services you don't need

# Example: Remove cAdvisor if no container monitoring needed
# Just comment out cadvisor service
docker-compose restart prometheus
```

---

## ✅ Monthly Checklist

- [ ] Disk space check (docker system df)
- [ ] Backup verified (restore test recommended)
- [ ] Security: Check Cloudflare logs → Access → Activity
- [ ] Password rotation (if applicable)
- [ ] Dependencies updated (docker-compose pull)
- [ ] Logs reviewed for errors/warnings
- [ ] Performance trends analyzed (grafana)
- [ ] Disaster recovery plan tested

---

## 🔗 Quick Command Reference

```bash
# Status & logs
docker-compose ps
docker-compose logs -f [SERVICE]
docker-compose logs -f --tail=100

# Restart & stop
docker-compose restart
docker-compose restart [SERVICE]
docker-compose stop
docker-compose down

# Clean up
docker system prune -a
docker volume prune

# Exec into container
docker exec -it [CONTAINER] bash

# Export/import
docker-compose config
docker system export

# Networks & volumes
docker network ls
docker volume ls
docker volume inspect [VOLUME_NAME]
```

---

**Keep your infrastructure running smoothly. 🚀**
