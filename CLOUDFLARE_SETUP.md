# 🌐 Cloudflare Tunnel Setup Guide

**Zero-trust, no-port-forward access to your infrastructure dashboard.**

---

## Step 1: Create Tunnel in Cloudflare

### 1.1 Access Cloudflare Dashboard
```
https://dash.cloudflare.com/
```

### 1.2 Navigate to Access → Tunnels
```
Account Home
→ Zero Trust (left sidebar)
→ Networks → Tunnels
→ "Create a tunnel" button
```

### 1.3 Create New Tunnel
- **Name**: `gururaj-infra-control`
- **Type**: Select Docker (or Managed - doesn't matter, we'll use Docker anyway)
- **Click**: "Save"

### 1.4 Copy Your Tunnel Token
After creation, you'll see:
```
TOKEN: eyJhIjov...
```

**COPY THIS VALUE**. You'll need it for `.env`.

---

## Step 2: Configure DNS Routing

### 2.1 Add Wildcard CNAME Record
In your domain's DNS settings, add:

```
Type:   CNAME
Name:   * (wildcard - all subdomains)
Target: <TUNNEL_UUID>.cfargotunnel.com
TTL:    Auto / 3600
```

**Example:**
```
Type:   CNAME
Name:   *.gururajseethur.in
Target: abc123.cfargotunnel.com
TTL:    Auto
```

✅ This routes ALL subdomains to your tunnel:
- `dashboard.gururajseethur.in`
- `prometheus.gururajseethur.in`
- `ollama.gururajseethur.in`
- `grafana.gururajseethur.in`

### 2.2 Verify DNS Propagation
```bash
nslookup dashboard.gururajseethur.in
# Should resolve to Cloudflare
```

---

## Step 3: Configure Local `.env`

### 3.1 Create `.env` from Template
```bash
cd gururajseethur-infra
cp .env.template .env
```

### 3.2 Edit `.env` with Tunnel Token
```bash
# .env
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjov...  # <-- Paste token here
DOMAIN=gururajseethur.in
GRAFANA_ADMIN_PASSWORD=YourStrongPassword123!
TRAEFIK_CERTIFICATESEMAIL=admin@gururajseethur.in
```

---

## Step 4: Deploy

### 4.1 Run Deployment Script
```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

### 4.2 Verify Tunnel Connection
```bash
docker logs cloudflared

# You should see:
# [INFO] Connected to Cloudflare.
# Tunnel credentials file created successfully.
```

---

## Step 5: Test Access

### 5.1 Visit Your Dashboard
```
https://dashboard.gururajseethur.in
```

**First access:**
- May take 1-2 minutes (Let's Encrypt TLS challenge)
- You'll see a 5-second redirect delay (tunnel propagation)
- Then: Grafana login page ✅

### 5.2 Login
```
Username: admin
Password: (from GRAFANA_ADMIN_PASSWORD in .env)
```

### 5.3 Test Other Endpoints
```
https://prometheus.gururajseethur.in    → Prometheus UI
https://ollama.gururajseethur.in/api/tags → Ollama API (JSON)
```

---

## 🔐 Security Considerations

### Basic Auth
All non-Grafana endpoints require Basic Auth:
- **Username**: `admin`
- **Password**: `admin` (CHANGE THIS!)

**To generate new password:**
```bash
# Install Apache utilities
sudo apt-get install apache2-utils

# Generate password hash
htpasswd -c -b hash.txt admin YourNewPassword

# Copy hash from hash.txt into config/traefik/dynamic.yml
```

### IP Allowlisting (Optional, via Cloudflare)
In Cloudflare Zero Trust dashboard:
```
Access → Applications → (Create Policy)
Rule: "IP address" in [your-ip-range]
Effect: Allow
```

### Rotate Tunnel Token
If compromised:
1. Delete tunnel in Cloudflare
2. Create new tunnel (get new token)
3. Update `.env`
4. Redeploy: `./scripts/deploy.sh`

---

## 🔄 Tunnel Lifecycle

### Restart Tunnel
```bash
docker-compose restart cloudflared
```

### Check Tunnel Status in Cloudflare
```
https://dash.cloudflare.com/
Zero Trust → Tunnels
→ Your tunnel → View details
→ Connections tab (should show 1 active connection)
```

### Connection Lost?
**Automatic recovery:** Tunnel reconnects within 30 seconds.

If stuck:
```bash
docker-compose logs cloudflared          # Check logs
docker compose down cloudflared
docker compose up -d cloudflared
```

---

## 🌍 Remote Access Testing

### From Your Device (any network)
```bash
# No VPN, no port forwarding needed
curl https://prometheus.gururajseethur.in/api/v1/query?query=up \
  -u admin:admin

# Should see:
{
  "status": "success",
  "data": {...}
}
```

### Via Browser
```
https://dashboard.gururajseethur.in
→ Works from any computer, any network ✅
```

---

## 🚀 Advanced: Custom Routes

### Route Specific Subdomains
Edit **Cloudflare Dashboard** for fine-grained control:

```
Zero Trust → Tunnels → Your Tunnel → Configure
→ Public Hostname

Add route:
- Application: dashboard.gururajseethur.in
- Type: HTTP
- URL: http://grafana:3000

Add route:
- Application: prometheus.gururajseethur.in
- Type: HTTP
- URL: http://prometheus:9090
```

(Our docker-compose already does this via Traefik labels, so extra step usually not needed.)

---

## 🆘 Troubleshooting

### Tunnel Showing "Disconnected" in Cloudflare UI
```bash
# Restart tunnel
docker-compose restart cloudflared

# Wait 30s, check again in Cloudflare dashboard
```

### Getting 504 Bad Gateway
```
Check:
1. docker-compose ps → All services running?
2. docker logs grafana → Any errors?
3. Traefik labels correct in docker-compose.yml?
```

### DNS Not Resolving
```bash
# Clear DNS cache
sudo systemctl restart systemd-resolved

# Test again
dig dashboard.gururajseethur.in
```

### HTTPS Certificate Error
```
Wait 2 minutes (Let's Encrypt challenge in progress)
Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+F5 (Windows/Linux)
```

---

## 📋 Checklist

- [ ] Tunnel created in Cloudflare
- [ ] Tunnel token copied to `.env`
- [ ] Domain DNS updated with CNAME wildcard
- [ ] `.env` configured completely
- [ ] `./scripts/deploy.sh` executed
- [ ] `docker logs cloudflared` shows "Connected"
- [ ] `https://dashboard.gururajseethur.in` is accessible
- [ ] Login works (admin/password)
- [ ] Other subdomains accessible (prometheus, ollama)
- [ ] Works from multiple networks/devices

---

**Your infrastructure is now accessible globally, securely, without exposed ports. 🔒**
