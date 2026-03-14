# Architecture

Sahayakan follows a **Control Plane / Data Plane** separation with event-driven orchestration.

## System Overview

```
                    Users / CLI / Web UI
                           |
                           v
                +----- Control Plane -----+
                | FastAPI API Server      |
                | Event Bus Processor     |
                | Cron Scheduler          |
                | PostgreSQL Metadata     |
                +------------+------------+
                             |
                             v
                +------ Data Plane -------+
                | Agent Runner            |
                | Issue Triage Agent      |
                | PR Context Agent        |
                | Meeting Summary Agent   |
                | Slack Digest Agent      |
                | Insights Agent          |
                | Trend Analysis Agent    |
                | Gemini LLM Client      |
                | Knowledge Cache (Git)   |
                | MinIO (Blob Storage)    |
                +-------------------------+
```

## Components

### Control Plane

The control plane handles orchestration, scheduling, and API access:

- **API Server** (FastAPI) — REST API for all operations
- **Event Bus** — PostgreSQL-backed event system for agent communication
- **Scheduler** — Cron-based job scheduling
- **Webhook Receiver** — Processes GitHub webhook events
- **Auth Middleware** — API key validation with RBAC scopes

### Data Plane

The data plane executes agent pipelines:

- **Agent Runner** — Orchestrates the 5-step agent lifecycle
- **Agents** — Six specialized analysis agents
- **LLM Client** — Google Gemini integration via REST API
- **Knowledge Cache** — Git repository for versioned data storage
- **Embeddings** — pgvector-based semantic search

### Infrastructure

- **PostgreSQL** (pgvector) — Metadata, events, embeddings, auth
- **MinIO** — Blob storage for large artifacts
- **Docker Compose** — Container orchestration
- **Caddy** — Reverse proxy with automatic TLS (production)

## Data Flow

### Ingestion Flow

```
GitHub/Jira/Slack → Fetcher → Knowledge Cache (Git) → Embeddings (pgvector)
```

1. Data fetchers pull from external APIs
2. Structured data is stored as JSON in the Git-based knowledge cache
3. Content is embedded as vectors for semantic search

### Agent Execution Flow

```
Job Created → Agent Runner → 5-Step Lifecycle → Artifacts → Event Published
```

1. A job is created (via API, CLI, webhook, or schedule)
2. The agent runner loads the appropriate agent
3. The agent executes its 5-step lifecycle (with optional review gates)
4. Outputs are stored in the knowledge cache and database
5. A completion event is published to the event bus

### Event-Driven Orchestration

```
Agent A completes → Event published → Event bus → Agent B triggered
```

Events flow through the PostgreSQL-backed event bus, allowing agents to trigger each other. For example, a GitHub webhook can trigger Issue Triage, which publishes an event that could trigger related analyses.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API Server | Python 3.12, FastAPI |
| Frontend | React, Material UI, Vite |
| LLM | Google Gemini (via REST API) |
| Database | PostgreSQL 16 with pgvector |
| Blob Storage | MinIO |
| Knowledge Store | Git repository |
| Containers | Docker Compose |
| Reverse Proxy | Caddy (automatic TLS) |

## Project Structure

```
sahayakan/
├── control-plane/          # API server, event bus, scheduler
│   └── api-server/         # FastAPI application
├── data-plane/             # Agent execution engine
│   ├── agent_runner/       # Runner, contracts, knowledge cache
│   ├── agents/             # 6 agent implementations
│   ├── llm_client/         # Gemini LLM client
│   └── prompts/            # Version-controlled prompt templates
├── ingestion/              # GitHub, Jira, Slack fetchers
├── web-ui/                 # React dashboard
├── cli/                    # Command-line tool
├── infrastructure/         # Docker Compose, migrations, Helm chart
├── tests/                  # Unit, integration, e2e tests
└── docs/                   # Documentation
```
