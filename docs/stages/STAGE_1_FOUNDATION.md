# Stage 1: Foundation

## Goal

Set up the project skeleton, infrastructure services, database schema, and API server scaffold. After this stage, you have a running system with PostgreSQL, MinIO, and a FastAPI server that can accept requests.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+
- Node.js 20+ (for later stages)
- Google Cloud project with Vertex AI enabled
- GitHub personal access token
- Jira API token

## Tasks

### 1.1 Repository Structure

Create the monorepo directory layout:

```
sahayakan/
+-- control-plane/
|   +-- api-server/
|       +-- app/
|       |   +-- __init__.py
|       |   +-- main.py
|       |   +-- config.py
|       |   +-- models/
|       |   |   +-- __init__.py
|       |   |   +-- agents.py
|       |   |   +-- jobs.py
|       |   |   +-- runs.py
|       |   |   +-- artifacts.py
|       |   |   +-- events.py
|       |   +-- routes/
|       |   |   +-- __init__.py
|       |   |   +-- agents.py
|       |   |   +-- jobs.py
|       |   |   +-- logs.py
|       |   |   +-- knowledge.py
|       |   +-- services/
|       |   |   +-- __init__.py
|       |   |   +-- job_service.py
|       |   +-- database.py
|       +-- requirements.txt
|       +-- Dockerfile
+-- infrastructure/
|   +-- docker-compose.yml
|   +-- db/
|       +-- migrations/
|           +-- 001_initial_schema.sql
+-- knowledge-cache/
|   +-- .gitkeep
+-- tests/
    +-- __init__.py
```

### 1.2 Docker Compose Setup

Services to define:

| Service    | Image              | Port  | Purpose              |
| ---------- | ------------------ | ----- | -------------------- |
| postgres   | postgres:16        | 5432  | Metadata database    |
| minio      | minio/minio        | 9000  | Blob storage         |
| api-server | built from source  | 8000  | FastAPI application  |

Environment variables:

```
POSTGRES_USER=sahayakan
POSTGRES_PASSWORD=<secure>
POSTGRES_DB=sahayakan

MINIO_ROOT_USER=sahayakan
MINIO_ROOT_PASSWORD=<secure>

GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json
VERTEX_PROJECT=<gcp-project-id>
VERTEX_LOCATION=us-central1
```

### 1.3 PostgreSQL Schema

Create the initial migration `001_initial_schema.sql`:

**agents** - Registered agents

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0',
    description TEXT,
    container_image TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**jobs** - Requested executions (control plane)

```sql
CREATE TYPE job_status AS ENUM (
    'pending', 'running', 'completed', 'failed',
    'cancelled', 'awaiting_review'
);

CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    status job_status DEFAULT 'pending',
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**agent_runs** - Actual execution records

```sql
CREATE TYPE run_status AS ENUM (
    'started', 'collecting_data', 'analyzing',
    'generating_output', 'storing_artifacts',
    'completed', 'failed', 'awaiting_review'
);

CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    agent_name TEXT NOT NULL,
    status run_status DEFAULT 'started',
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    git_commit TEXT,
    logs_uri TEXT
);
```

**artifacts** - Outputs from agent runs

```sql
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    artifact_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**events** - Agent Bus

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);
```

**llm_usage** - Gemini API tracking

```sql
CREATE TABLE llm_usage (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    model TEXT NOT NULL,
    tokens_input INTEGER,
    tokens_output INTEGER,
    latency_ms INTEGER,
    estimated_cost DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**agent_subscriptions** - Event subscriptions

```sql
CREATE TABLE agent_subscriptions (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    event_type TEXT NOT NULL,
    UNIQUE(agent_name, event_type)
);
```

**review_gates** - Optional human review configuration

```sql
CREATE TABLE review_gates (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL REFERENCES agents(name),
    stage TEXT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    UNIQUE(agent_name, stage)
);

CREATE TABLE review_decisions (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,  -- 'approved' or 'rejected'
    reviewer TEXT,
    comments TEXT,
    decided_at TIMESTAMP DEFAULT NOW()
);
```

**indexes**

```sql
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_agent ON jobs(agent_name);
CREATE INDEX idx_runs_job ON agent_runs(job_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_processed ON events(processed);
CREATE INDEX idx_llm_usage_run ON llm_usage(run_id);
```

### 1.4 FastAPI Application Scaffold

`main.py` - Application entry point with:
- CORS middleware
- Database connection lifecycle
- Route registration for `/agents`, `/jobs`, `/logs`, `/knowledge`
- Health check endpoint `GET /health`

`config.py` - Settings loaded from environment:
- Database URL
- MinIO endpoint and credentials
- Vertex AI project/location
- Knowledge cache path

`database.py` - Async database connection using `asyncpg` or `SQLAlchemy async`

### 1.5 API Endpoints (Scaffold)

These return basic responses; full implementation comes in later stages:

```
GET  /health                    -> system status
GET  /agents                    -> list registered agents
GET  /agents/{name}             -> get agent details
POST /agents/register           -> register new agent
POST /jobs/run                  -> create a new job
GET  /jobs                      -> list jobs
GET  /jobs/{id}                 -> get job details
```

### 1.6 Knowledge Cache Initialization

Create the Git-based knowledge cache directory structure:

```
knowledge-cache/
+-- github/
|   +-- issues/
|   +-- pull_requests/
+-- jira/
|   +-- tickets/
+-- meetings/
|   +-- transcripts/
+-- agent_outputs/
|   +-- issue_analysis/
|   +-- pr_context/
|   +-- meeting_summaries/
+-- events/
```

Initialize as a Git repository (separate from the main sahayakan repo).

## Deliverables

- [ ] `docker-compose up` starts PostgreSQL, MinIO, and API server
- [ ] Database schema applied successfully
- [ ] `GET /health` returns `200 OK`
- [ ] `POST /agents/register` creates an agent record
- [ ] `GET /agents` returns registered agents
- [ ] `POST /jobs/run` creates a job record with status `pending`
- [ ] Knowledge cache directory initialized as Git repo

## Definition of Done

You can run `docker-compose up`, hit the health endpoint, register an agent, and create a job. The job sits in `pending` status. The knowledge cache directory exists with the correct structure.
