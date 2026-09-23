# 🚀 AI Control Plane

**One-click AI infrastructure. No technical knowledge required.**

AI Control Plane is a fully managed, self-hosted platform for running and monitoring AI models. Deploy in minutes, scale with ease.

---

## ⚡ Quick Start

### First-Time Installation
```bash
bash install/install.sh
```

That's it. The installer will:
- Check system requirements (Docker)
- Ask for your domain and email
- Generate secure configuration
- Start everything automatically
- Print your app URL

### After Installation
Open your browser:
```
https://app.<your-domain>
```

---

## 🎯 What You Get

### AI Chat Interface
- Talk to AI models instantly
- Support for multiple models
- Simple, clean interface

### Real-Time Monitoring
- See active requests
- Track latency and performance
- View error rates
- Monitor system health

### Automatic Scaling
- All infrastructure managed
- No manual configuration needed
- Runs on your own server

---

## 🔧 System Requirements

**Minimum:**
- Docker (any modern version)
- 4GB RAM
- 10GB disk space
- Linux/macOS/Windows (WSL2)

**Recommended for Production:**
- 8+ cores CPU
- 16GB+ RAM
- 50GB+ SSD space
- Ubuntu 20.04+ or similar

---

## 📋 Supported Platforms

- ✅ **Linux** (Ubuntu, Debian, CentOS, etc.)
- ✅ **macOS** (Intel & Apple Silicon)
- ✅ **Windows** (with WSL2 + Docker Desktop)
- ✅ **Cloud** (AWS, DigitalOcean, Vultr, Linode, etc.)

---

## 🌐 Domain & Networking

You need:
1. **A domain name** (e.g., example.com)
2. **Cloudflare account** (free tier is fine)
3. **Cloudflare Tunnel token** (secure, zero-knowledge proxy)

The installer will guide you through setup.

### Why Cloudflare Tunnel?
- ✅ No port forwarding needed
- ✅ DDoS protection
- ✅ Automatic HTTPS/SSL
- ✅ Zero-trust security
- ✅ Free to use

---

## 📊 Features

### Chat
- Real-time AI responses
- Multiple model support
- Streaming responses
- Simple, responsive UI

### Monitoring
- **Requests/second** — see throughput in real-time
- **Active requests** — how many AI tasks running now
- **Latency P95** — 95th percentile response time
- **Error rate** — catch issues early

### Health Status
- System status at a glance
- Service health indicators
- Clear error messages

### Zero Configuration
- Config auto-generated during install
- Sensible defaults
- No manual server setup

---

## 🚀 Deployment

### Local/Development
```bash
bash install/install.sh
# Follow the prompts
```

### Production Server
Same process:
```bash
# SSH into your server
ssh user@your-server.com

# Clone the repo
git clone https://github.com/gururajseethur/self-hosted-ai-infrastructure.git
cd self-hosted-ai-infrastructure

# Run installer
bash install/install.sh
```

That's it. No Docker knowledge required.

---

## 🔒 Security

### Data Privacy
- All data stays on your server
- No cloud vendor lock-in
- You own your data

### Encryption
- HTTPS everywhere (Let's Encrypt)
- Automatic certificate renewal
- TLS 1.2+ only

### Access Control
- Admin authentication required
- Cloudflare Tunnel authentication
- No public port exposure

---

## 💰 Pricing

**AI Control Plane:** Free (open source)

**Your Operating Costs:**
- **Cloud Server:** $5-50/month (depending on provider)
- **Cloudflare:** Free (includes Tunnel)
- **Domain:** $10-15/year

**Total:** ~$5-50/month + domain

---

## 📈 Use Cases

### 1. Personal AI Assistant
- Run your own ChatGPT
- Keep data private
- Full control

### 2. Team Collaboration
- Internal AI service for your team
- Track usage and performance
- Predictable costs

### 3. Business SaaS
- White-label for your customers
- Usage-based pricing
- Built-in monitoring

### 4. Developer Tool
- AI for code generation
- Local inference (no API calls)
- Integrated with your workflows

---

## 🛠️ Customization

### Change AI Models
Edit `.env` or UI to switch models:
- ```bash
  docker compose exec ollama ollama pull llama2
  ```

### Add Custom Endpoints
Extend the backend at `app/backend/main.py`

### Modify UI
Edit frontend at `app/frontend/index.html`

---

## 📞 Support & Documentation

- **Getting Started:** See QUICKSTART.md
- **Advanced Setup:** See CLOUDFLARE_SETUP.md
- **Troubleshooting:** See OPERATIONS_GUIDE.md
- **Developer Docs:** See exporter documentation

---

## 🤝 Contributing

Community contributions welcome:
```bash
git fork https://github.com/gururajseethur/self-hosted-ai-infrastructure.git
git checkout -b feature/your-feature
git commit -am "Add feature"
git push origin feature/your-feature
git pull-request
```

---

## 📋 Health Check

After installation, verify everything is working:

```bash
# Check if all services are running
docker compose ps

# View app logs
docker compose logs app

# Test API
curl https://app.<your-domain>/api/health
```

---

## 🔄 Maintenance

### Update AI Models
```bash
docker exec ollama ollama pull <new-model>
```

### Backup Your Data
```bash
bash scripts/backup.sh
```

### Restart Services
```bash
bash scripts/restart.sh
```

### Stop Everything
```bash
bash scripts/stop.sh
```

---

## ⚠️ Important Notes

### Before Going Public

1. **Cloudflare Tunnel Setup** — Required for external access
   - Free with any Cloudflare account
   - No port forwarding needed
   - Automatic HTTPS

2. **Firewall Rules** — No changes needed
   - System runs fully inside Docker
   - No listening ports on host
   - Safe behind Cloudflare

3. **Let's Encrypt SSL** — Automatic
   - Renewal is automatic
   - No manual intervention needed

### Performance Tuning

- **CPU-bound**: More cores = faster AI inference
- **Memory**: 8GB+ recommended for larger models
- **Disk**: Models take 4-10GB each

---

## 💡 Tips

- Start with a small model (e.g., `neural-chat`)
- Monitor usage dashboard regularly
- Back up configuration regularly
- Set alerts for error rates

---

## 🎓 Learning Resources

- **Docker Basics:** https://docs.docker.com/get-started/
- **Ollama Docs:** https://ollama.ai
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/

---

## 📄 License

Proprietary. For internal use and future monetization.

---

## 🎯 Next Steps

1. **Install:** `bash install/install.sh`
2. **Access:** `https://app.<your-domain>`
3. **Chat:** Start using AI immediately
4. **Monitor:** Check stats in real-time
5. **Customize:** Add features as needed

---

**Questions?** Check the logs or restart the system. Everything is designed to be self-healing.
