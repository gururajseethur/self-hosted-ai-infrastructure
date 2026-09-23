# 🗑️ Uninstall Guide

## Overview

The uninstall script (`scripts/uninstall.sh`) cleanly removes the AI Control Plane deployment while preserving or destroying data as you choose.

---

## Quick Start

### Choose Your Path

**Option 1: Remove Everything (Clean Slate)**
```bash
bash scripts/uninstall.sh --force
```
- ✗ Stops all services
- ✗ Removes containers
- ✗ Removes network
- ✗ Deletes all data volumes (DESTRUCTIVE)
- ✓ Backs up .env file

**Option 2: Keep Your Data**
```bash
bash scripts/uninstall.sh --keep-volumes
```
- ✗ Stops all services
- ✗ Removes containers
- ✗ Removes network
- ✓ Preserves all volumes (metrics, dashboards, models)
- Helpful: Manual volume removal commands provided

**Option 3: Interactive (Recommended)**
```bash
bash scripts/uninstall.sh
```
- Shows warnings and what will be removed
- Asks for confirmation (type "uninstall")
- Prompts for each major decision
- Most control and safety

---

## What Gets Removed

### Always Removed
- ✗ All running containers (app, ollama, prometheus, grafana, etc.)
- ✗ Docker network (infra)
- ✗ ACME certificate cache (./acme.json)

### Conditionally Removed
- ✗ **Data volumes** (prometheus_data, grafana_data, ollama_data) — **ONLY if NOT using `--keep-volumes`**
- ✗ **.env file** — Backed up first, then optionally deleted

### Always Preserved
- ✓ Source code (scripts, config, app, exporter dirs)
- ✓ Git history and documentation

---

## Command Reference

### Basic Uninstall (Interactive)
```bash
cd /path/to/self-hosted-ai-infrastructure
bash scripts/uninstall.sh
```

**Prompts:**
```
This will:
  1. Stop all AI Control Plane services
  2. Remove Docker containers
  3. Remove Docker network
  4. Remove all data volumes (⚠️ DESTRUCTIVE)
  5. Backup .env file (optional)

Are you sure? (type 'uninstall' to confirm):
```

### Non-Interactive Uninstall
```bash
bash scripts/uninstall.sh --force
```
- Skips all confirmation prompts
- Automatically removes data
- Automatically backs up & removes .env

### Keep Data (for Reinstall)
```bash
bash scripts/uninstall.sh --keep-volumes
```
- Preserves all volumes
- Speeds up reinstall if recurring
- Useful for testing/iteration

### Combine Options
```bash
bash scripts/uninstall.sh --keep-volumes --force
```
- Keeps data AND skips prompts
- Removes containers/network quickly

---

## Step-by-Step Process

### Step 1: Stop Services
```
[1/4] Stopping services...
```
- Runs `docker compose down`
- Gracefully stops all containers
- Preserves or marks volumes for removal

### Step 2: Remove Volumes
```
[2/4] Removing data volumes...
```
**Unless `--keep-volumes` used:**
- prometheus_data (metrics history)
- grafana_data (dashboards, settings)
- ollama_data (cached AI models)

**If `--keep-volumes` used:**
- Shows locations where data is stored
- Provides manual removal commands

### Step 3: Clean Docker Network
```
[3/4] Cleaning up Docker network...
```
- Removes the internal `infra` network
- Other networks unaffected

### Step 4: Handle .env File
```
[4/4] Handling .env file...
```
- Automatically backs up to `.env.backup.<timestamp>`
- **In interactive mode:** asks if you want to delete it
- **In force mode:** backs up only (doesn't delete)

---

## Data Recovery

### Backup Location
```
/path/to/repo/.env.backup.1707343200
```

### Recover Backed Up .env
```bash
cp .env.backup.1707343200 .env
docker compose up -d
```

### Restore from Volume Backup
If you removed volumes accidentally:

```bash
# View available volume backups
ls -la /var/lib/docker/volumes/

# Restore if you have external backups
# (outside scope of uninstall tool)
```

---

## Common Scenarios

### Scenario 1: Uninstall to Reinstall
```bash
# Keep data for quick reinstall
bash scripts/uninstall.sh --keep-volumes --force

# Later, reinstall:
bash install/install.sh

# Old data will be used by new instance
```

### Scenario 2: Full Cleanup (Move to New Server)
```bash
# Backup .env for reference
bash scripts/uninstall.sh

# Keep backup for reference
cat .env.backup.* > .env.archive

# Move repo to new server
git clone https://github.com/your-org/self-hosted-ai-infrastructure.git
cd self-hosted-ai-infrastructure
```

### Scenario 3: Uninstall from Cron (Automated)
```bash
#!/bin/bash
# Uninstall with no prompts
/path/to/repo/scripts/uninstall.sh --keep-volumes --force
# Then backup volumes
docker run --rm -v infra_prometheus_data:/data -v /backup:/backup \
  ubuntu tar czf /backup/prometheus_data.tar.gz -C /data .
```

### Scenario 4: Troubleshoot (Stop Without Removing)
```bash
# Don't use uninstall! Use compose instead:
docker compose down              # Keeps data, stops services
docker compose up -d            # Restarts services

docker compose restart app      # Restart specific service
docker compose logs app -f      # View logs
```

---

## Manual Cleanup (Alternative)

If you prefer to manually uninstall:

```bash
# Stop containers
docker compose down

# Remove network
docker network rm infra

# Remove volumes individually
docker volume rm infra_ollama_data
docker volume rm infra_prometheus_data
docker volume rm infra_grafana_data

# Remove .env if desired
rm .env
```

---

## Verification

### Check Everything is Removed
```bash
# No running containers
docker compose ps
# Should show: "No such file or directory"

# No infra network
docker network ls | grep infra
# Should return: (nothing)

# No data volumes
docker volume ls | grep infra
# Should return: (nothing)
```

---

## Safety Features

| Feature | Benefit |
|---------|---------|
| **Confirmation Prompt** | Can't accidentally uninstall |
| **Backup .env** | Can recover credentials later |
| **`--keep-volumes`** | Don't lose data by mistake |
| **`--force` Awareness** | Skips prompts when intended |
| **Colored Output** | ⚠️ Warnings clearly visible |
| **Step-by-Step** | See what's happening at each stage |

---

## Troubleshooting

### "Permission Denied"
```bash
# Make script executable
chmod +x scripts/uninstall.sh
```

### "docker compose: command not found"
```bash
# Ensure Docker Compose is installed
docker compose version

# If not installed, install it and try again
```

### "Cannot connect to Docker daemon"
```bash
# Start Docker daemon
sudo systemctl start docker

# Or use sudo
sudo bash scripts/uninstall.sh
```

### "Volume is in use"
```bash
# Ensure all containers are stopped
docker compose down

# Then run uninstall
bash scripts/uninstall.sh
```

---

## FAQ

**Q: Can I undo an uninstall?**
A: Only if you used `--keep-volumes`. Data is preserved in Docker volumes. Run `install/install.sh` again to redeploy.

**Q: Where are my backups?**
A: The .env file is backed up with a timestamp: `.env.backup.<UNIX_TIMESTAMP>`

**Q: What about the Cloudflare Tunnel?**
A: Uninstall script doesn't touch Cloudflare. You need to manually delete it:
```bash
cloudflared tunnel delete ai-control-plane
```

**Q: Can I reinstall without Cloudflare?**
A: Yes! Use `bash install/install.sh --skip-cloudflare`

**Q: Is data really deleted?**
A: Docker volumes are removed. To truly securely erase: `docker run --rm -v <volume>:/data alpine rm -rf /data/*`

**Q: How do I uninstall but keep the repository?**
A: Run uninstall script—it only removes containers/volumes, not source code!

---

## Next Steps

### After Uninstall

1. **If reinstalling:**
   ```bash
   bash install/install.sh
   ```

2. **If archiving:**
   ```bash
   tar czf infra_backup_$(date +%s).tar.gz .
   ```

3. **If moving servers:**
   ```bash
   git clone https://github.com/your-org/self-hosted-ai-infrastructure.git
   cd self-hosted-ai-infrastructure
   bash install/install.sh
   ```

### Cleanup Beyond Uninstall

```bash
# Remove repository entirely
cd ..
rm -rf self-hosted-ai-infrastructure

# Clean up all Docker (careful!)
docker system prune -a --volumes

# Clean up Cloudflare Tunnel
cloudflared tunnel delete ai-control-plane
```

---

## Summary

- ✅ **Safe by default** — Interactive prompts prevent mistakes
- ✅ **Data-aware** — `--keep-volumes` preserves data
- ✅ **Flexible** — Multiple options for different scenarios
- ✅ **Clean** — Removes ALL traces (except source code)
- ✅ **Reversible** — Can reinstall from same directory

**Status:** Production-ready uninstall tool ✓
