# API Reference

The Sahayakan API server exposes a REST API built with FastAPI. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

**Base URL**: `http://localhost:8000` (local) or `https://your-domain.com/api` (production)

## Authentication

When `AUTH_ENABLED=true`, all endpoints (except public ones) require an API key:

```bash
curl -H "Authorization: Bearer sk_your-api-key" http://localhost:8000/agents
```

**Public endpoints** (no key required): `/health`, `/docs`, `/openapi.json`, `/redoc`

### API Key Scopes

| Scope | Access |
|-------|--------|
| `read` | GET endpoints |
| `write` | POST/PUT endpoints |
| `admin` | All endpoints including key management |

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| GET | `/metrics` | Prometheus metrics |

### Agents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List registered agents |
| GET | `/agents/{name}` | Get agent details |
| POST | `/agents/register` | Register a new agent |
| GET | `/agents/{name}/gates` | Get review gates |
| PUT | `/agents/{name}/gates` | Update review gates |

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs` | List jobs (supports `?status=`, `?limit=`) |
| GET | `/jobs/{id}` | Get job details |
| POST | `/jobs/run` | Create and run a new job |
| POST | `/jobs/{id}/review` | Submit review decision |

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingestion/github/sync` | Trigger GitHub sync |
| GET | `/ingestion/github/status` | GitHub sync status |
| POST | `/ingestion/jira/sync` | Trigger Jira sync |
| GET | `/ingestion/jira/status` | Jira sync status |
| POST | `/ingestion/slack/sync` | Trigger Slack sync |
| GET | `/ingestion/slack/status` | Slack sync status |

### Knowledge & Search

| Method | Path | Description |
|--------|------|-------------|
| GET | `/knowledge/reports` | List reports |
| GET | `/knowledge/reports/{type}/{id}` | Get a specific report |
| POST | `/knowledge/search` | Semantic search |
| GET | `/knowledge/search/stats` | Embedding statistics |

### Repositories

| Method | Path | Description |
|--------|------|-------------|
| GET | `/repositories` | List repositories |
| POST | `/repositories` | Add a repository |
| PUT | `/repositories/{id}` | Update a repository |
| DELETE | `/repositories/{id}` | Delete a repository |

### GitHub App

| Method | Path | Description |
|--------|------|-------------|
| GET | `/github-app` | List GitHub Apps |
| POST | `/github-app` | Add a GitHub App |
| PUT | `/github-app/{id}` | Update a GitHub App |
| DELETE | `/github-app/{id}` | Delete a GitHub App |
| POST | `/github-app/{id}/installations` | Add an installation |
| POST | `/github-app/{id}/test` | Test connection |

### Jira Projects

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jira-projects` | List Jira projects |
| POST | `/jira-projects` | Add a Jira project |
| PUT | `/jira-projects/{id}` | Update a Jira project |
| DELETE | `/jira-projects/{id}` | Delete a Jira project |

### Schedules

| Method | Path | Description |
|--------|------|-------------|
| GET | `/schedules` | List schedules |
| POST | `/schedules` | Create a schedule |
| PUT | `/schedules/{id}` | Update a schedule |
| DELETE | `/schedules/{id}` | Delete a schedule |

### Events

| Method | Path | Description |
|--------|------|-------------|
| GET | `/events` | List events (supports `?event_type=`, `?limit=`) |

### Logs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/logs/{job_id}` | Get job logs |
| WS | `/ws/logs/{job_id}` | Stream logs in real-time |

### Usage

| Method | Path | Description |
|--------|------|-------------|
| GET | `/usage/summary` | LLM usage summary |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/github` | GitHub webhook receiver |

### Auth & API Keys

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api-keys` | List API keys |
| POST | `/api-keys` | Create an API key |
| DELETE | `/api-keys/{id}` | Revoke an API key |
| GET | `/audit-log` | View audit log |

### Insights

| Method | Path | Description |
|--------|------|-------------|
| GET | `/insights` | List detected insights |

!!! tip
    Visit `http://localhost:8000/docs` for interactive Swagger documentation where you can try out API calls directly.
