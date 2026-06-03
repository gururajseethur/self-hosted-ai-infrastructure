# PHASE 2 Installer Enhancement - Quick Reference

## What's Changed

The installer (`install/install.sh`) has been upgraded with production-grade features:

### 🎯 Key Features

1. **Input Validation** - Domain/email checked with regex, must be valid to proceed
2. **DNS Verification** - Checks if domain is resolvable (informational, non-blocking)
3. **Cloudflare Tunnel Wizard** - Interactive setup with token validation
4. **Health Checks** - Post-deployment verification of all services
5. **Logging** - All steps logged to `install.log` for debugging
6. **Better Errors** - Clear messages with suggested recovery steps

### 📊 Installation Flow

```
[1/7] Docker Check ✓
[2/7] Docker Compose Check ✓
[3/7] Configuration (domain, email, validate DNS)
[4/7] Generate .env (auto-password)
[5/7] Cloudflare Tunnel Setup (interactive)
[6/7] Deploy services
[7/7] Health Check (verify all running)
```

### 🚀 Usage

**Standard installation:**
```bash
bash install/install.sh
```

**Skip Cloudflare prompts:**
```bash
bash install/install.sh --skip-cloudflare
```

### 📋 What You'll See

```
🚀 AI Control Plane - One-Click Installer

[1/7] Checking Docker...
✓ Docker found: Docker version 24.0.0

[2/7] Checking Docker Compose...
✓ Docker Compose found: Docker Compose v2.24.0

[3/7] Configuration
Please provide your configuration.

  Domain name (e.g., example.com): mycompany.com
  Admin email (for SSL certificates): admin@mycompany.com
  
  Checking DNS for mycompany.com... ✓

[4/7] Generating configuration (.env)...
✓ Configuration saved to .env

[5/7] Cloudflare Tunnel Setup
  You need a Cloudflare Tunnel for secure external access.
  
  Do you have a Cloudflare Tunnel token? (y/n): y
  Paste your Cloudflare Tunnel token: ••••••••••••••••
  ✓ Token saved

[6/7] Deploying AI Control Plane...
  This may take 2-5 minutes on first run (downloading images).
  [... docker compose output ...]
✓ Deployment completed

[7/7] Verifying deployment...
  ✓ Backend API responding
  ✓ Ollama service healthy
  ✓ Prometheus service healthy

✓ AI Control Plane Installation Complete!

🎉 Next Steps:

  📱 Access your AI Control Plane:
     https://app.mycompany.com

  🔑 Domain: mycompany.com
  📧 Email: admin@mycompany.com

📊 Admin Access (internal network only):
  Dashboard:  https://dashboard.mycompany.com
  Prometheus: https://prometheus.mycompany.com
  Credentials:
    User: admin
    Password: [auto-generated strong password]

📖 Helpful Commands:

  View logs:
    docker compose logs app -f

  Check service status:
    docker compose ps

  View installer log:
    cat install.log
```

### ✨ New Helper Functions

All added to the script for reusability:

| Function | Purpose |
|----------|---------|
| `log_step()` | Append timestamped message to install.log |
| `check_dns()` | Validate domain is resolvable |
| `check_cloudflare_tunnel()` | Validate token format |
| `wait_for_service()` | Poll service port (30 attempts) |
| `run_health_check()` | Verify app, ollama, prometheus responding |

### 🔧 Error Handling

If something fails, the installer:
1. Shows clear error message
2. Suggests debug commands (`docker compose logs`, `docker compose ps`)
3. Logs all output to `install.log`
4. Guides user on recovery steps

### 📝 Log File

All installation steps are logged to `install.log`:

```bash
cat install.log
# [14:23:45] Configuration complete
# [14:24:12] Deployment completed
# [14:24:45] Health checks passed
```

### 🎬 Next (PHASE 3)

- Lock Grafana/Prometheus to internal-only access
- Add admin monitoring dashboard
- Implement billing dashboard
- Add uninstall script

---

**Full Details:** See [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)
