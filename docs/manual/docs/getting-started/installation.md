# Installation

## Clone the Repository

```bash
git clone https://github.com/sahayakan/sahayakan.git
cd sahayakan
```

## Automated Setup

The setup script creates a virtual environment, installs dependencies, and configures pre-commit hooks:

```bash
bash setup.sh
# Or:
make setup
```

## Configure Environment

Copy the example environment file and edit it with your credentials:

```bash
cp infrastructure/.env.example .env
```

Key variables to configure:

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Database username (default: `sahayakan`) |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name (default: `sahayakan`) |
| `MINIO_ROOT_USER` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | MinIO secret key |
| `GEMINI_API_KEY` | Google Gemini API key for LLM analysis |
| `AUTH_ENABLED` | Set to `false` for local development |

## Start Services

```bash
cd infrastructure
docker compose --env-file ../.env up --build -d
```

This starts four services:

| Service | URL | Description |
|---------|-----|-------------|
| **API Server** | `http://localhost:8000` | FastAPI backend |
| **Web UI** | `http://localhost:3000` | React dashboard |
| **PostgreSQL** | `localhost:5433` | Database (port 5433 to avoid conflicts) |
| **MinIO** | `http://localhost:9001` | Object storage console |

## Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","version":"0.1.0"}
```

Visit `http://localhost:3000` in your browser to access the web dashboard.

## Stop Services

```bash
make stop
# Or:
cd infrastructure && docker compose --env-file ../.env down
```
