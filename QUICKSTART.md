# ⚡ Quick Start (5 Minutes)

**Set up your infrastructure control platform in 5 steps.**

---

## 1️⃣ Prerequisites ✓

```bash
# Check Docker installed
docker --version
docker-compose --version

# Both should output version info (v20+)
```

If Docker not installed:
```bash
# macOS
brew install docker

# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# Start Docker daemon
sudo systemctl start docker
sudo usermod -aG docker $USER  # Run Docker without sudo
```

---

## 2️⃣ Clone & Configure (2 min)

```bash
# Clone this repo
git clone https://github.com/gururajseethur/self-hosted-ai-infrastructure.git
cd self-hosted-ai-infrastructure

# Create .env file
cp .env.template .env

# Open and edit
nano .env
```

**Edit `.env` with:**
```ini
# Get this from Cloudflare (instructions below)
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjov...

# Your domain
DOMAIN=gururajseethur.in

# Create strong password
GRAFANA_ADMIN_PASSWORD=MySecurePassword123!

# Your email (for Let's Encrypt)
TRAEFIK_CERTIFICATESEMAIL=admin@gururajseethur.in
```

**Don't have Cloudflare Tunnel token yet?**
→ See [CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md)

---

## 3️⃣ Deploy (1 min)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy
./scripts/deploy.sh

# Should output:
# ✅ Deployment complete!
# ⏳ Services starting up (1-2 minutes)...
```

---

## 4️⃣ Verify (1 min)

```bash
# Check all services running
docker-compose ps

# All should say "Up" (not "Exited")
```

```bash
# Check tunnel connected
docker logs cloudflared | grep "Connected"

# Should see: [INFO] Connected to Cloudflare tunnel
```

---

## 5️⃣ Access (1 min)

**Open your browser:**
```
https://dashboard.gururajseethur.in
```

**Login:**
```
Username: admin
Password: (from GRAFANA_ADMIN_PASSWORD in .env)
```

**You're in! 🎉**

---

## 🎯 Next Steps

### See Your Metrics
- CPU, Memory, Disk
- Container status
- Ollama health
- Network traffic

### Access Other Endpoints
```
https://prometheus.gururajseethur.in    → Prometheus
https://ollama.gururajseethur.in/api/tags → Ollama API
```

Basic Auth:
```
Username: admin
Password: admin
```

### Common Commands

```bash
# View all services
docker-compose ps

# Check specific service
docker-compose logs grafana

# Restart services
./scripts/restart.sh

# Stop everything
./scripts/stop.sh

# Check health
./scripts/status.sh
```

---

## 🆘 Troubleshooting

### Dashboard not loading?
```bash
# Wait 2 minutes (Grafana cold start + TLS)
# Then hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+F5 (Linux/Windows)

# Check logs
docker logs grafana | tail -20
```

### Can't access from outside?
```bash
# Verify tunnel connected
docker logs cloudflared

# Check Cloudflare dashboard
https://dash.cloudflare.com/
→ Zero Trust → Tunnels → Your Tunnel → Connections

# Should show "Active"
```

### Service "Exited"?
```bash
# Check why
docker-compose logs SERVICE_NAME

# Restart
docker-compose restart SERVICE_NAME
```

---

## 📚 Full Documentation

- **[README.md](README.md)** — Complete architecture & operations
- **[CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md)** — Tunnel configuration
- **[OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)** — Daily/emergency operations

---

## ✅ Success Checklist

- [ ] Docker installed and running
- [ ] `.env` configured with tunnel token
- [ ] `./scripts/deploy.sh` executed
- [ ] `docker-compose ps` shows all "Up"
- [ ] Cloudflare tunnel shows "Connected"
- [ ] `https://dashboard.gururajseethur.in` loads
- [ ] Grafana login works
- [ ] Metrics visible in dashboard

---

**You're running a production infrastructure platform. Secure, portable, observable. 🚀**
