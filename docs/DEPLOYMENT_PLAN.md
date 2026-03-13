# Sahayakan Deployment Plan

**Target Server**: Debian 13 (trixie) on AWS
**Domain**: `ai.helm-team.org`
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
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker admin
# Re-login for group to take effect (or use `sg docker -c '...'` for immediate access)
```

> **Note**: On Debian 13, the package is `docker-compose` (not `docker-compose-plugin`).
> Docker Compose v2 is included and accessible as `docker compose` (subcommand).

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
git clone https://github.com/sahayakan/sahayakan.git
cd sahayakan
```

> The repo is public, so HTTPS clone works without authentication.
> The CD pipeline uses `git fetch origin main` over HTTPS.

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

**Option A — With domain** (`ai.helm-team.org`) (currently deployed):

Same route list as Option B below, but wrapped in a domain block.
Caddy automatically provisions and renews a Let's Encrypt TLS certificate.
HTTP requests are redirected to HTTPS (308).

```
# /etc/caddy/Caddyfile
ai.helm-team.org {
    handle /health {
        reverse_proxy localhost:8000
    }
    # ... all other API route handles (same as Option B) ...
    handle {
        reverse_proxy localhost:3000
    }
}
```

**Option B — IP-only (no TLS)**:

Since the API routes are at the root (e.g., `/health`, `/agents`, `/jobs`), each route prefix
must be explicitly mapped. The catch-all sends everything else to the web UI.

```
# /etc/caddy/Caddyfile
:80 {
    handle /health        { reverse_proxy localhost:8000 }
    handle /metrics       { reverse_proxy localhost:8000 }
    handle /agents/*      { reverse_proxy localhost:8000 }
    handle /api-keys/*    { reverse_proxy localhost:8000 }
    handle /audit-log/*   { reverse_proxy localhost:8000 }
    handle /auth/*        { reverse_proxy localhost:8000 }
    handle /events/*      { reverse_proxy localhost:8000 }
    handle /ingestion/*   { reverse_proxy localhost:8000 }
    handle /insights/*    { reverse_proxy localhost:8000 }
    handle /jobs/*        { reverse_proxy localhost:8000 }
    handle /knowledge/*   { reverse_proxy localhost:8000 }
    handle /logs/*        { reverse_proxy localhost:8000 }
    handle /schedules/*   { reverse_proxy localhost:8000 }
    handle /search/*      { reverse_proxy localhost:8000 }
    handle /teams/*       { reverse_proxy localhost:8000 }
    handle /usage/*       { reverse_proxy localhost:8000 }
    handle /webhooks/*    { reverse_proxy localhost:8000 }
    handle /ws/*          { reverse_proxy localhost:8000 }
    handle /docs          { reverse_proxy localhost:8000 }
    handle /openapi.json  { reverse_proxy localhost:8000 }

    handle { reverse_proxy localhost:3000 }
}
```

> When adding new API routes, remember to add the prefix to the Caddyfile.

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

### 6.2 GitHub Secrets Setup (One-Time)

Three secrets must be configured in the GitHub repository. This was done via `gh` CLI:

```bash
# Set SSH private key
gh secret set DEPLOY_SSH_KEY < ~/.ssh/baijumk1.pem --repo sahayakan/sahayakan

# Set server IP
echo "13.126.248.229" | gh secret set DEPLOY_SERVER_IP --repo sahayakan/sahayakan

# Set SSH known hosts (prevents MITM attacks)
ssh-keyscan 13.126.248.229 2>/dev/null | gh secret set DEPLOY_SSH_KNOWN_HOSTS --repo sahayakan/sahayakan
```

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

### 6.6 Server One-Time Setup

The following was performed to prepare the server for CD (these steps only need to be done once):

1. Installed `git`, `curl`, `docker.io`, `docker-compose`, `caddy`, `ufw`, `fail2ban` on Debian 13
2. Enabled Docker daemon: `sudo systemctl enable --now docker`
3. Added `admin` user to `docker` group: `sudo usermod -aG docker admin`
4. Cloned repo: `git clone https://github.com/sahayakan/sahayakan.git /home/admin/sahayakan`
5. Created production `.env` with generated passwords (`openssl rand -base64 24`)
6. Started all services: `docker compose -f docker-compose.prod.yml --env-file ../.env up -d`
7. Configured Caddy reverse proxy (IP-only mode, Option B) with all API route prefixes
8. Configured firewall: `ufw allow 22,80,443/tcp` + deny all other incoming
9. Enabled fail2ban with SSH jail
10. Added three GitHub secrets via `gh secret set`

### 6.7 Checklist

- [x] Add `DEPLOY_SSH_KEY` secret to GitHub repo
- [x] Add `DEPLOY_SERVER_IP` secret to GitHub repo
- [x] Add `DEPLOY_SSH_KNOWN_HOSTS` secret to GitHub repo
- [x] Install git, docker, docker-compose on server
- [x] Clone repo and create production `.env` on server
- [x] Start services on server
- [x] Push a commit to `main` and verify CI -> Deploy chain
- [x] Verify services after automated deploy

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

## Disk Layout

A 100GB EBS volume (`vol-0d5c096c225e7d210`) is attached as `/dev/xvdf` and mounted at `/data`:

| Path | Contents |
|---|---|
| `/data/docker` | Docker data-root (images, containers, volumes) |
| `/data/backups` | Daily database backups (symlinked from `/home/admin/backups`) |

The root disk (8GB) holds only the OS, packages, and repo checkout. The fstab entry uses
`LABEL=sahayakan-data` with `nofail` so the server boots even if the volume is detached.

Monitor disk usage: `df -h / /data` and `docker system df`

---

## Checklist

- [x] SSH into server and update system
- [x] Install Docker, Docker Compose
- [x] Clone repo and create production `.env`
- [x] Start services with `docker-compose.prod.yml`
- [x] Verify all services healthy
- [x] Set up GitHub secrets for CD
- [x] Test CI -> Deploy pipeline end-to-end
- [x] Install Caddy, fail2ban
- [x] Configure firewall (ufw) — SSH/80/443 only
- [x] Configure Caddy reverse proxy — all API routes + web UI on port 80
- [x] Point domain (`ai.helm-team.org`) and enable HTTPS via Let's Encrypt
- [x] Set up log rotation — Docker daemon: 10MB max, 3 files per container
- [x] Set up automated backups — daily at 3 AM UTC, 7-day retention
- [x] Enable unattended security updates — daily apt update + auto-install + weekly autoclean
- [x] Attach EBS volume (`vol-0d5c096c225e7d210`, 100GB) mounted at `/data`
