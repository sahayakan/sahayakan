# Stage 6: Stabilization & Polish

## Goal

Harden the system with error handling, cost tracking, CLI tool, comprehensive testing, and deployment configuration. After this stage, the MVP is production-ready for internal use.

## Dependencies

- Stage 5 completed (all agents and event bus working)

## Tasks

### 6.1 Error Handling & Resilience

**Gemini API failures:**

```python
class GeminiClient:
    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # seconds

    def generate(self, prompt, model):
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._call_vertex_ai(prompt, model)
                return response
            except RateLimitError:
                wait = self.BACKOFF_BASE ** attempt
                log(f"Rate limited, retrying in {wait}s")
                sleep(wait)
            except TimeoutError:
                log(f"Timeout on attempt {attempt + 1}")
                if attempt == self.MAX_RETRIES - 1:
                    raise
            except Exception as e:
                log_error(f"Unexpected error: {e}")
                raise
```

**Agent failure handling:**
- Failed jobs are marked with error details in the database
- Agent runner captures exception traceback in logs
- Structured error response stored as artifact:

```json
{
  "status": "error",
  "error_type": "llm_timeout",
  "message": "Vertex AI request timed out after 3 retries",
  "stage": "analyze",
  "traceback": "..."
}
```

**GitHub/Jira API failures:**
- Retry with backoff for rate limits
- Partial sync: record which items succeeded/failed
- Ingestion status endpoint reports failures

**Database connection handling:**
- Connection pooling with health checks
- Graceful degradation if DB is temporarily unreachable

### 6.2 Cost Tracking Dashboard

**LLM cost calculation:**

| Model            | Input (per 1K tokens) | Output (per 1K tokens) |
| ---------------- | --------------------- | ---------------------- |
| Gemini 1.5 Pro   | $0.00125              | $0.005                 |
| Gemini 1.5 Flash | $0.000075             | $0.0003                |

(Prices as of MVP development - update as needed)

**Cost tracking API:**

```
GET /usage/summary                -> total tokens, cost by period
GET /usage/by-agent               -> breakdown by agent
GET /usage/by-model               -> breakdown by model
GET /usage/daily                  -> daily usage over time
```

**UI: Cost Dashboard Widget**

On the main dashboard:
- Total cost this month
- Cost trend chart (daily)
- Top agents by cost
- Average cost per run

### 6.3 CLI Tool

`cli/sahayakan`:

A command-line tool for developers to interact with the platform locally.

**Commands:**

```bash
# Agent operations
sahayakan agent list                          # List registered agents
sahayakan agent info <name>                   # Agent details
sahayakan agent gates <name>                  # Show review gates
sahayakan agent gates <name> --set after_analysis=true  # Configure gate

# Job operations
sahayakan run issue-triage --issue 231        # Run issue triage agent
sahayakan run pr-context --pr 143             # Run PR context agent
sahayakan run meeting-summary --transcript standup-2026-03-13
sahayakan job list                            # List jobs
sahayakan job status <id>                     # Job details
sahayakan job logs <id>                       # Stream logs (live)
sahayakan job logs <id> --follow              # Follow log stream
sahayakan job review <id> --approve           # Approve paused job
sahayakan job review <id> --reject "reason"   # Reject paused job

# Ingestion
sahayakan sync github                         # Trigger GitHub sync
sahayakan sync jira                           # Trigger Jira sync
sahayakan sync status                         # Sync status

# Knowledge
sahayakan report list                         # List reports
sahayakan report view <type> <id>             # View a report
sahayakan knowledge search <query>            # Search knowledge cache

# Events
sahayakan events list                         # Recent events
sahayakan events tail                         # Stream events live

# System
sahayakan status                              # System health
sahayakan usage                               # LLM usage summary
```

**Implementation:**

`cli/sahayakan` is a Python CLI using `click` or `typer`:

```
cli/
+-- sahayakan/
|   +-- __init__.py
|   +-- main.py
|   +-- commands/
|   |   +-- agent.py
|   |   +-- job.py
|   |   +-- sync.py
|   |   +-- report.py
|   |   +-- events.py
|   |   +-- system.py
|   +-- api_client.py
+-- setup.py
```

**Configuration:**

```yaml
# ~/.sahayakan/config.yaml
api_url: http://localhost:8000
```

### 6.4 Agent Resource Limits

Enforce resource limits in Docker:

```yaml
agent-runner:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "1.0"
```

Per-agent limits configurable:

```python
AGENT_LIMITS = {
    "issue-triage": {
        "max_runtime_seconds": 300,
        "max_llm_calls": 5,
        "max_tokens_per_call": 4000,
    },
    "pr-context": {
        "max_runtime_seconds": 600,
        "max_llm_calls": 10,
        "max_tokens_per_call": 8000,
    },
    "meeting-summary": {
        "max_runtime_seconds": 600,
        "max_llm_calls": 5,
        "max_tokens_per_call": 16000,
    },
}
```

Runner enforces timeouts and kills agents that exceed limits.

### 6.5 Data Privacy & Sanitization

**Input sanitization before LLM calls:**

```python
def sanitize_for_llm(text: str) -> str:
    """Remove sensitive data before sending to Gemini."""
    # Remove patterns matching:
    # - API keys / tokens
    # - Email addresses (optional, configurable)
    # - Internal URLs
    # - Credentials in code blocks
    return sanitized_text
```

**Configuration:**

```yaml
sanitization:
  remove_api_keys: true
  remove_emails: false
  remove_internal_urls: true
  custom_patterns:
    - "password\\s*=\\s*['\"].*['\"]"
```

### 6.6 Testing

**Unit tests** (`tests/unit/`):

- Agent contract compliance (each agent implements all methods)
- LLM client retry logic
- Knowledge cache read/write/commit
- Event bus subscription matching
- Review gate logic
- Input sanitization
- Cost calculation

**Integration tests** (`tests/integration/`):

- API server endpoints (all routes)
- Job lifecycle: pending -> running -> completed
- Job lifecycle with review gate: pending -> running -> awaiting_review -> completed
- Event chain: event published -> subscription matched -> job created
- GitHub ingestion -> knowledge cache storage
- Jira ingestion -> knowledge cache storage
- Log streaming via WebSocket

**End-to-end tests** (`tests/e2e/`):

- Full pipeline: GitHub sync -> Issue Triage -> report generated
- Full pipeline: PR ingestion -> PR Context -> report generated
- Full pipeline: transcript upload -> Meeting Summary -> report generated
- Event chain: issue ingestion -> triage -> PR context triggered
- Review gate flow through UI

**Test fixtures:**
- Sample GitHub issue JSON
- Sample PR JSON
- Sample Jira ticket JSON
- Sample meeting transcript
- Mock Gemini responses

### 6.7 Deployment Configuration

**Production Docker Compose** (`infrastructure/docker-compose.prod.yml`):

Additions over development:
- Volume mounts for persistent data (PostgreSQL, MinIO, knowledge-cache)
- Restart policies (`restart: unless-stopped`)
- Health checks for all services
- Log rotation
- Environment variable files (`.env.prod`)

**Backup strategy:**
- PostgreSQL: daily `pg_dump` to MinIO
- Knowledge cache: Git push to remote (GitHub/GitLab)
- MinIO: sync to backup location

**Monitoring:**
- Health check endpoint: `GET /health` returns status of all services
- Docker health checks for all containers

### 6.8 Configuration & Secrets Management

**Environment structure:**

```
infrastructure/
+-- .env.example        # Template with all variables
+-- .env.dev            # Development defaults
+-- .env.prod           # Production values (not committed)
```

**Required environment variables:**

```bash
# Database
POSTGRES_USER=sahayakan
POSTGRES_PASSWORD=
POSTGRES_DB=sahayakan
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# MinIO
MINIO_ROOT_USER=sahayakan
MINIO_ROOT_PASSWORD=
MINIO_ENDPOINT=minio:9000

# Vertex AI
GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json
VERTEX_PROJECT=
VERTEX_LOCATION=us-central1

# GitHub
GITHUB_TOKEN=
GITHUB_REPOS=owner/repo1,owner/repo2

# Jira
JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
JIRA_PROJECT_KEYS=PROJ

# Knowledge Cache
KNOWLEDGE_CACHE_PATH=/data/knowledge-cache

# API Server
API_HOST=0.0.0.0
API_PORT=8000
```

### 6.9 Documentation

**README.md** (project root):
- Project overview
- Quick start guide
- Architecture diagram
- API reference link
- CLI usage

**API documentation:**
- Auto-generated from FastAPI (Swagger/OpenAPI at `/docs`)

## Deliverables

- [ ] Retry logic for Gemini, GitHub, and Jira APIs
- [ ] Structured error responses for all failure modes
- [ ] Cost tracking API and dashboard widget
- [ ] CLI tool with all core commands
- [ ] Agent resource limits enforced
- [ ] Input sanitization before LLM calls
- [ ] Unit tests for core logic
- [ ] Integration tests for API and pipelines
- [ ] E2E tests for full agent workflows
- [ ] Production Docker Compose with persistence and health checks
- [ ] Backup configuration
- [ ] Environment variable management
- [ ] README and API documentation

## Definition of Done

The MVP is complete when:

1. All three agents run autonomously end-to-end
2. Event bus triggers agent chains automatically
3. Review gates can pause any agent at any stage
4. Logs stream in real-time to the web UI
5. Reports are browsable in the dashboard
6. CLI tool can run agents and view results
7. Costs are tracked and visible
8. Errors are handled gracefully with retries
9. Tests pass (unit, integration, e2e)
10. System runs reliably via `docker-compose up` on a Linux VM
11. Complete audit trail: every agent action has a Git commit, database record, and event
