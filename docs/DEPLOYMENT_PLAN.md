# Sahayakan Deployment Plan

**Target Server**: Debian 13 (trixie) on AWS
**IP**: 13.126.248.229
**SSH**: `ssh -i ~/.ssh/baijumk1.pem admin@13.126.248.229`
**Resources**: 8 GB RAM, 8 GB disk

---

## Phase 1: Server Preparation

### 1.1 System Update & Essentials

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget ufw fail2ban
```

### 1.2 Install Docker & Docker Compose

```bash
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker admin
# Re-login for group to take effect
```

### 1.3 Firewall Setup

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Caddy)
sudo ufw allow 443/tcp   # HTTPS (Caddy)
sudo ufw enable
```

> Internal ports (5432, 8000, 9000, 9001, 3000) are NOT exposed publicly.
> Only Caddy reverse-proxy ports (80/443) are open.

### 1.4 Install Caddy (Reverse Proxy + Auto-TLS)

```bash
sudo apt install -y caddy
```

---

## Phase 2: Deploy Application

### 2.1 Clone Repository

```bash
cd /home/admin
git clone git@github.com:sahayakan/sahayakan.git
cd sahayakan
```

### 2.2 Create Production `.env`

Copy from the example and fill in real credentials:

```bash
cp infrastructure/.env.example .env
```

Key values to set:

| Variable | Notes |
|---|---|
| `POSTGRES_PASSWORD` | Generate strong password: `openssl rand -base64 24` |
| `MINIO_ROOT_PASSWORD` | Generate strong password |
| `GITHUB_TOKEN` | Personal access token with repo scope |
| `AUTH_ENABLED` | `true` for production |

### 2.3 Start Services

```bash
cd infrastructure
docker compose -f docker-compose.prod.yml --env-file ../.env up -d
```

### 2.4 Verify Services

```bash
docker compose -f docker-compose.prod.yml ps
# Check API health
curl http://localhost:8000/health
# Check web UI
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

---

## Phase 3: Reverse Proxy & TLS

### 3.1 Configure Caddy

> If a domain is available, Caddy provides automatic HTTPS.
> Without a domain, use IP-based access on port 80 only.

**Option A — With domain** (e.g., `sahayakan.example.com`):

```
# /etc/caddy/Caddyfile
sahayakan.example.com {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /ws/* {
        reverse_proxy localhost:8000
    }
    handle {
        reverse_proxy localhost:3000
    }
}
```

**Option B — IP-only (no TLS)**:

```
# /etc/caddy/Caddyfile
:80 {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /ws/* {
        reverse_proxy localhost:8000
    }
    handle {
        reverse_proxy localhost:3000
    }
}
```

```bash
sudo systemctl restart caddy
```

---

## Phase 4: Production Hardening

### 4.1 Systemd Service (Auto-restart)

Docker Compose services already have `restart: unless-stopped`. Docker itself should be enabled:

```bash
sudo systemctl enable docker
```

### 4.2 Log Rotation

```bash
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

```bash
sudo systemctl restart docker
```

### 4.3 Automated Backups

Create a daily cron job using the existing backup script:

```bash
# /home/admin/sahayakan/scripts/prod-backup.sh
#!/bin/bash
cd /home/admin/sahayakan
bash infrastructure/scripts/backup.sh /home/admin/backups/$(date +%Y-%m-%d)
# Keep only last 7 days
find /home/admin/backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
```

```bash
chmod +x scripts/prod-backup.sh
crontab -e
# Add: 0 3 * * * /home/admin/sahayakan/scripts/prod-backup.sh >> /home/admin/backups/backup.log 2>&1
```

### 4.4 Fail2Ban (SSH protection)

```bash
sudo systemctl enable --now fail2ban
```

### 4.5 Unattended Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Phase 5: Deployment Workflow

### 5.1 Manual Deploy (from local machine)

```bash
# From local machine
ssh -i ~/.ssh/baijumk1.pem admin@13.126.248.229 \
  "cd /home/admin/sahayakan && git pull && cd infrastructure && docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build"
```

### 5.2 Deploy Script (local convenience)

Create a local deploy script at `scripts/deploy.sh`:

```bash
#!/bin/bash
set -euo pipefail
source .env.local

echo "Deploying to $AWS_SERVER_IP..."
ssh -i "$SSH_KEY_PATH" admin@"$AWS_SERVER_IP" bash -s <<'REMOTE'
  cd /home/admin/sahayakan
  git pull origin main
  cd infrastructure
  docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build
  echo "--- Health check ---"
  sleep 5
  curl -sf http://localhost:8000/health && echo " API OK" || echo " API FAILED"
REMOTE
echo "Deploy complete."
```

---

## Phase 6: Continuous Deployment

### 6.1 Overview

The CD pipeline chains off the existing CI workflow. When CI passes on `main`, a deploy workflow automatically SSHs into the production server, pulls the latest code, rebuilds services, and verifies health.

**Flow**: Push to `main` -> CI (lint + test) -> Deploy (if CI passes)

### 6.2 GitHub Secrets Setup

Three secrets must be configured in the GitHub repository settings (Settings > Secrets and variables > Actions):

| Secret | Value |
|---|---|
| `DEPLOY_SSH_KEY` | Contents of `~/.ssh/baijumk1.pem` |
| `DEPLOY_SERVER_IP` | `13.126.248.229` |
| `DEPLOY_SSH_KNOWN_HOSTS` | Output of `ssh-keyscan 13.126.248.229` |

### 6.3 How It Works

- **Trigger**: Uses `workflow_run` event — the deploy job runs only after the "CI" workflow completes successfully on `main`.
- **Concurrency**: The `deploy-production` concurrency group ensures only one deploy runs at a time. `cancel-in-progress: false` lets a running deploy finish before the next one starts.
- **Deploy steps**: Fetches latest `main`, rebuilds `api-server` then `web-ui` one at a time (keeping postgres/minio running), verifies health checks.

### 6.4 Rollback Mechanism

If any step fails during deployment (build failure, health check timeout, curl failure):
1. The deploy script automatically resets to the previous commit SHA (recorded before the update)
2. Rebuilds `api-server` and `web-ui` from that previous commit
3. The workflow exits with a failure status, visible in the GitHub Actions UI

### 6.5 Skipping a Deploy

- **Commit message**: Include `[skip deploy]` in the commit message to skip deployment even if CI passes.
- **Branch**: Pushes to non-`main` branches never trigger deployment (CI runs but deploy does not).

### 6.6 Checklist

- [ ] Add `DEPLOY_SSH_KEY` secret to GitHub repo
- [ ] Add `DEPLOY_SERVER_IP` secret to GitHub repo
- [ ] Add `DEPLOY_SSH_KNOWN_HOSTS` secret to GitHub repo
- [ ] Push a commit to `main` and verify CI -> Deploy chain
- [ ] Verify services after automated deploy

---

## Resource Budget (8 GB RAM)

| Service | Memory Limit | Notes |
|---|---|---|
| PostgreSQL + pgvector | 1 GB | Set in compose `deploy.resources` |
| API Server | 512 MB | Set in compose |
| Web UI (serve) | 128 MB | Static file server, minimal |
| MinIO | 512 MB | Object storage |
| Caddy | 64 MB | Reverse proxy |
| OS + headroom | ~5.8 GB | Comfortable margin |

---

## Disk Considerations

With only 8 GB total disk, space is tight. Priorities:

1. Consider attaching an EBS volume for `/home/admin/backups` and Docker volumes
2. Monitor disk usage: `df -h /` and `docker system df`
3. Prune unused images regularly: `docker image prune -f`
4. Keep backup retention short (7 days) or offload to S3

---

## Checklist

- [ ] SSH into server and update system
- [ ] Install Docker, Docker Compose, Caddy, fail2ban
- [ ] Configure firewall (ufw)
- [ ] Clone repo and create production `.env`
- [ ] Start services with `docker-compose.prod.yml`
- [ ] Configure Caddy reverse proxy
- [ ] Verify all services healthy
- [ ] Set up log rotation
- [ ] Set up automated backups
- [ ] Enable unattended security updates
- [ ] Test deploy script from local machine
- [ ] (Optional) Attach EBS volume for data
- [ ] (Optional) Point domain and enable HTTPS
