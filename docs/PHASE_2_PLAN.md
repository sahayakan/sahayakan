# Sahayakan - Phase 2 Master Plan

## Context

Phase 1 (MVP) delivered a working agent platform with three agents, event-driven orchestration, review gates, a web dashboard, and a CLI. Phase 2 evolves the platform from a functional MVP into a production-grade intelligence system.

## Phase 2 Goals

1. **Semantic memory** - Agents can search knowledge by meaning, not just keywords
2. **Slack integration** - Ingest Slack conversations and post agent results
3. **Scheduled automation** - Agents run on schedules without manual triggers
4. **Insights engine** - Agents detect patterns across time and produce long-term insights
5. **Authentication & multi-tenancy** - Secure the platform for team use
6. **Production hardening** - Real Vertex AI integration, monitoring, backups

## Phase 2 Architecture

```
                    Users / Slack / Webhooks
                           |
                           v
                +----- Control Plane ------+
                | API Server + Auth        |
                | Scheduler (cron jobs)    |
                | Event Bus               |
                | Notification Service    |
                +------------+-------------+
                             |
                             v
                +------- Data Plane -------+
                | Agent Runner             |
                | MVP Agents (3)           |
                | Insights Agent (new)     |
                | Slack Digest Agent (new) |
                | Code Review Agent (new)  |
                |                          |
                | Gemini (Vertex AI)       |
                | Knowledge Cache (Git)    |
                | Vector Store (pgvector)  |
                | MinIO (Blob Storage)     |
                +--------------------------+
```

## Phase 2 Stages

| Stage | Name                        | Description                                                    |
| ----- | --------------------------- | -------------------------------------------------------------- |
| 7     | Semantic Memory             | pgvector, embeddings, semantic search across knowledge cache   |
| 8     | Slack Integration           | Slack ingestion, bot notifications, Slack digest agent          |
| 9     | Scheduled Automation        | Cron-based job scheduling, GitHub webhooks, auto-ingestion      |
| 10    | Insights Engine             | Long-term pattern detection, insights table, insights agent    |
| 11    | Auth & Multi-tenancy        | API keys, GitHub OAuth, per-team data isolation                |
| 12    | Production Hardening        | Real Vertex AI, monitoring, backups, Kubernetes-ready          |

---

## Stage 7: Semantic Memory

### Goal

Add vector-based semantic search so agents can find related content by meaning, not just keyword matching. This dramatically improves duplicate detection, context collection, and cross-referencing.

### Tasks

**7.1 pgvector Setup**

- Add pgvector extension to PostgreSQL
- Create embeddings table:

```sql
CREATE EXTENSION vector;

CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,     -- 'issue', 'pr', 'jira', 'report', 'transcript'
    source_id TEXT NOT NULL,       -- '2800', 'PROJ-123', etc.
    content_hash TEXT NOT NULL,    -- detect changes
    embedding vector(768),         -- Gemini embedding dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);

CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

**7.2 Embedding Service**

- Shared service that generates embeddings via Vertex AI Embeddings API
- Automatically embeds new content when ingested or when reports are generated
- Batch embedding for initial backfill of existing knowledge cache

```python
class EmbeddingService:
    def embed(self, text: str) -> list[float]:
        """Generate embedding via Vertex AI."""

    def embed_and_store(self, source_type: str, source_id: str, text: str):
        """Embed and upsert into embeddings table."""

    def search(self, query: str, source_types: list[str], limit: int = 10) -> list[dict]:
        """Semantic search across embedded content."""
```

**7.3 Agent Context Enhancement**

- Update `collect_context()` in all three agents to use semantic search
- Instead of keyword matching for related items, query the vector store:
  - "Find issues similar to this one" (duplicate detection)
  - "Find PRs related to this issue's topic"
  - "Find Jira tickets about this component"

**7.4 Search API**

```
POST /knowledge/search    -> semantic search across all content
  body: { "query": "auth timeout issues", "types": ["issue", "pr"], "limit": 10 }
```

**7.5 CLI & UI Updates**

- `sahayakan knowledge search "auth timeout"` CLI command
- Search bar in web UI knowledge browser

### Deliverables

- [ ] pgvector extension installed and embeddings table created
- [ ] Embedding service generates and stores embeddings
- [ ] All agents use semantic search in collect_context
- [ ] Search API endpoint working
- [ ] CLI and UI search functionality

---

## Stage 8: Slack Integration

### Goal

Ingest Slack conversations into the knowledge cache and post agent results back to Slack. Add a Slack Digest Agent that summarizes channel activity.

### Tasks

**8.1 Slack Data Ingestion**

- Slack Bot using Slack Web API (not Socket Mode for MVP)
- Fetch messages from configured channels
- Store in knowledge cache: `knowledge-cache/slack/channels/{channel}/`
- Incremental sync using `oldest` timestamp

```
ingestion/slack_fetcher/fetcher.py
```

Storage format:

```json
{
  "channel": "engineering",
  "messages": [
    {"user": "alice", "text": "...", "ts": "...", "thread_replies": [...]}
  ],
  "fetched_at": "..."
}
```

**8.2 Slack Notification Service**

- Post agent results to configured Slack channels
- Configurable per-agent: which channel to notify
- Message formatting with report summary, links, and priority badges
- Triggered by agent completion events

```
control-plane/notifications/slack_notifier.py
```

**8.3 Slack Digest Agent**

New agent that summarizes Slack channel activity:

- Input: channel name + time range
- Output: key discussions, decisions, action items, mentioned issues/PRs
- Prompt template: `data-plane/prompts/slack_digest.prompt`
- Report: `knowledge-cache/agent_outputs/slack_digests/{channel}_{date}.md`

**8.4 Event Integration**

- `slack.synced` event triggers Slack Digest Agent
- Agent results can be posted back to Slack via notification service

**8.5 Configuration**

```yaml
slack:
  bot_token: ${SLACK_BOT_TOKEN}
  channels:
    - name: engineering
      notify_on: [issue.analyzed, pr.analyzed]
    - name: standup
      notify_on: [meeting.summarized]
  digest_schedule: "daily"
```

### Deliverables

- [ ] Slack fetcher ingests channel messages
- [ ] Slack Digest Agent summarizes channel activity
- [ ] Agent results posted to Slack channels
- [ ] Event-driven: sync triggers digest, results trigger notification

---

## Stage 9: Scheduled Automation

### Goal

Agents run on schedules and react to webhooks without manual triggers. The system becomes truly autonomous.

### Tasks

**9.1 Job Scheduler**

- Cron-like scheduler that creates jobs on a schedule
- Stored in database:

```sql
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    cron_expression TEXT NOT NULL,   -- e.g., '*/10 * * * *'
    parameters JSONB,
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

- Scheduler service polls `schedules` table and creates jobs when due

**9.2 GitHub Webhooks**

- Webhook endpoint: `POST /webhooks/github`
- Listens for:
  - `issues.opened` → publishes `issue.ingested` event
  - `pull_request.opened` → publishes `pr.ingested` event
  - `issue_comment.created` → re-fetches and re-analyzes issue
- Verifies webhook signature for security

**9.3 Scheduled Ingestion**

Default schedules:

| Schedule | Agent/Action | Frequency |
|----------|-------------|-----------|
| GitHub sync | Full repo sync | Every 10 minutes |
| Jira sync | Project sync | Every 30 minutes |
| Slack sync | Channel sync | Every hour |
| Slack digest | Digest agent | Daily at 9am |

**9.4 API & CLI**

```
POST /schedules              -> create schedule
GET  /schedules              -> list schedules
PUT  /schedules/{id}         -> update schedule
DELETE /schedules/{id}       -> delete schedule

sahayakan schedule list
sahayakan schedule create issue-triage --cron "*/10 * * * *" --param repo=org/project
```

### Deliverables

- [ ] Scheduler creates jobs on cron schedules
- [ ] GitHub webhooks trigger real-time agent runs
- [ ] Scheduled ingestion for GitHub, Jira, Slack
- [ ] Schedule management via API and CLI

---

## Stage 10: Insights Engine

### Goal

Agents analyze patterns across time and produce long-term insights: recurring bugs, slow components, team bottlenecks, technical debt signals.

### Tasks

**10.1 Insights Table**

```sql
CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    insight_type TEXT NOT NULL,    -- 'recurring_bug', 'slow_component', 'tech_debt', etc.
    title TEXT NOT NULL,
    description TEXT,
    evidence JSONB,                -- links to issues, PRs, analyses
    severity TEXT,                 -- 'low', 'medium', 'high', 'critical'
    confidence FLOAT,
    status TEXT DEFAULT 'active',  -- 'active', 'acknowledged', 'resolved'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**10.2 Insights Agent**

New agent that runs periodically to detect patterns:

- Scans all issue analyses for recurring themes (same component, similar errors)
- Detects PRs with high risk scores in the same area
- Identifies components with high bug density
- Finds action items from meetings that reference the same issues repeatedly

Output:

```json
{
  "insight_type": "recurring_bug",
  "title": "Repeated auth service timeouts",
  "description": "3 issues in the last month related to OAuth token refresh",
  "evidence": [
    {"type": "issue", "id": 231, "analysis_priority": "high"},
    {"type": "issue", "id": 198, "analysis_priority": "high"},
    {"type": "pr", "id": 143, "risk_level": "medium"}
  ],
  "severity": "high",
  "confidence": 0.85
}
```

**10.3 Trend Analysis Agent**

New agent that produces weekly/monthly trend reports:

- Issue volume trends (increasing/decreasing by component)
- PR merge time trends
- Bug vs. feature ratio
- Agent accuracy trends (when humans override agent suggestions)

**10.4 Insights Dashboard**

New web UI page:

- Active insights with severity badges
- Trend charts (issues over time, PR velocity, bug density)
- Acknowledge/resolve workflow for insights
- Drill-down to evidence (linked issues, PRs, analyses)

**10.5 Insights API**

```
GET  /insights                -> list insights (filterable)
GET  /insights/{id}           -> get insight details
PUT  /insights/{id}/status    -> acknowledge/resolve
GET  /insights/trends         -> trend data for charts
```

### Deliverables

- [ ] Insights agent detects recurring patterns
- [ ] Trend analysis agent produces periodic reports
- [ ] Insights stored in database with evidence links
- [ ] Insights dashboard with charts and drill-down
- [ ] Acknowledge/resolve workflow

---

## Stage 11: Authentication & Multi-tenancy

### Goal

Secure the platform for team use with authentication, authorization, and per-team data isolation.

### Tasks

**11.1 API Key Authentication**

- API keys stored in database (hashed)
- Required for all API calls (except /health)
- Passed via `Authorization: Bearer <key>` header

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    team_id INTEGER,
    scopes TEXT[],           -- ['read', 'write', 'admin']
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
```

**11.2 GitHub OAuth (optional)**

- Login with GitHub for the web UI
- Map GitHub users to teams
- Use GitHub organization membership for authorization

**11.3 Team Isolation**

- Add `team_id` to jobs, agents, events tables
- Each team has its own knowledge cache namespace
- Agents and reports scoped to team
- Admin team can see everything

**11.4 RBAC**

Roles:
- `viewer` - read access to reports, jobs, events
- `operator` - can run agents, approve reviews
- `admin` - can manage agents, schedules, team settings

**11.5 Audit Log**

- Log all API calls with user, action, timestamp
- Queryable via API for compliance

### Deliverables

- [ ] API key authentication on all endpoints
- [ ] Optional GitHub OAuth for web UI
- [ ] Per-team data isolation
- [ ] Role-based access control
- [ ] Audit log for all actions

---

## Stage 12: Production Hardening

### Goal

Make the system production-ready with real LLM integration, monitoring, backups, and container orchestration.

### Tasks

**12.1 Real Vertex AI Integration**

- Validate GeminiClient with real Vertex AI credentials
- Test with Gemini 1.5 Pro and Flash
- Configure model selection per agent (Pro for analysis, Flash for summaries)
- Token budget enforcement per job

**12.2 Monitoring & Alerting**

- Prometheus metrics endpoint (`/metrics`)
- Key metrics:
  - Job success/failure rate
  - Agent execution time (p50, p95, p99)
  - LLM API latency and error rate
  - Event processing lag
  - Database connection pool usage
- Grafana dashboard templates
- Alert rules for: agent failures, high costs, event lag

**12.3 Backup & Recovery**

- Automated PostgreSQL backups (pg_dump → MinIO, daily)
- Knowledge cache Git push to remote (hourly)
- MinIO replication to backup location
- Restore procedures documented and tested

**12.4 Kubernetes Deployment**

- Helm chart for all services
- Separate deployments for:
  - API server (2+ replicas)
  - Agent runner (scalable workers)
  - Event bus processor
  - Scheduler
- ConfigMaps and Secrets for configuration
- PersistentVolumeClaims for PostgreSQL and MinIO
- HorizontalPodAutoscaler for agent runners

**12.5 Knowledge Cache Remote Sync**

- Push knowledge cache Git repo to GitHub/GitLab
- Configure remote in knowledge cache Git config
- Periodic push after agent commits
- Pull before agent reads (handle merge conflicts)

**12.6 Graceful Shutdown & Job Recovery**

- Runner handles SIGTERM gracefully (finish current job, then exit)
- Jobs interrupted by crashes resume on restart (detect stale `running` jobs)
- Dead letter queue for repeatedly failing events

### Deliverables

- [ ] Real Vertex AI integration tested end-to-end
- [ ] Prometheus metrics and Grafana dashboards
- [ ] Automated backups with tested restore
- [ ] Helm chart for Kubernetes deployment
- [ ] Knowledge cache remote sync
- [ ] Graceful shutdown and job recovery

---

## Phase 2 Technology Additions

| Component | Technology | Stage |
|-----------|-----------|-------|
| Vector DB | pgvector (PostgreSQL extension) | 7 |
| Embeddings | Vertex AI Embedding API | 7 |
| Slack | Slack Web API + Bot | 8 |
| Scheduler | Custom (PostgreSQL-backed) | 9 |
| Webhooks | FastAPI webhook endpoints | 9 |
| Monitoring | Prometheus + Grafana | 12 |
| Orchestration | Kubernetes + Helm | 12 |

## Phase 2 New Agents

| Agent | Stage | Purpose |
|-------|-------|---------|
| Slack Digest Agent | 8 | Summarizes Slack channel activity |
| Insights Agent | 10 | Detects recurring patterns and technical debt |
| Trend Analysis Agent | 10 | Produces periodic trend reports |

## Success Criteria

Phase 2 is complete when:

1. Agents find related content via semantic search, not just keywords
2. Slack conversations are ingested and agent results posted to Slack
3. Agents run on schedules without manual triggers
4. The system detects and surfaces recurring patterns as insights
5. The platform is secured with authentication and team isolation
6. The system runs reliably on Kubernetes with monitoring and backups
