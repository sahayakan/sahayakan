# Sahayakan

Autonomous agentic AI platform for software development teams. Agents analyze GitHub issues, pull requests, and meeting transcripts to produce traceable reports with optional human review at any stage.

## Architecture

```
                    Users / CLI / Web UI
                           |
                           v
                +----- Control Plane -----+
                | FastAPI API Server      |
                | Event Bus Processor     |
                | PostgreSQL Metadata     |
                +------------+------------+
                             |
                             v
                +------ Data Plane -------+
                | Agent Runner            |
                | Issue Triage Agent      |
                | PR Context Agent        |
                | Meeting Summary Agent   |
                | Gemini (Vertex AI)      |
                | Knowledge Cache (Git)   |
                | MinIO (Blob Storage)    |
                +-------------------------+
```

## Quick Start

### Prerequisites

- Docker / Podman with Compose
- Python 3.12+
- Node.js 20+ (for web UI development)

### Start Services

```bash
cd infrastructure
cp .env.example .env.dev   # Edit with your settings
docker compose --env-file .env.dev up --build -d
```

Services:
- **API Server:** http://localhost:8000 (Swagger docs at `/docs`)
- **MinIO Console:** http://localhost:9001
- **Web UI:** http://localhost:3000 (run `cd web-ui && npm run dev`)

### Register Agents

```bash
curl -X POST http://localhost:8000/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "issue-triage", "version": "1.0", "description": "Analyzes GitHub issues"}'
```

### Run an Agent

```bash
# Via API
curl -X POST http://localhost:8000/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"agent": "issue-triage", "parameters": {"issue_id": 231}}'

# Via CLI
python3 -m cli.main run issue-triage --issue 231
```

### CLI Usage

```bash
python3 -m cli.main status                     # System health
python3 -m cli.main agent list                 # List agents
python3 -m cli.main run issue-triage --issue 1 # Run agent
python3 -m cli.main job list                   # List jobs
python3 -m cli.main job status 1               # Job details
python3 -m cli.main report list                # List reports
python3 -m cli.main report view issue_analysis 2800  # View report
python3 -m cli.main events list                # Recent events
python3 -m cli.main usage                      # LLM usage summary
```

## Agents

| Agent | Input | Output |
|-------|-------|--------|
| **issue-triage** | GitHub issue | Priority, duplicates, related PRs, suggested actions |
| **pr-context** | Pull request | Risk level, linked issues, review suggestions |
| **meeting-summary** | Meeting transcript | Action items, decisions, key topics |

## Key Features

- **Autonomous execution** with optional human review gates at any stage
- **Complete audit trail**: every action produces a Git commit, database record, and event
- **Event-driven orchestration**: agents trigger each other through the event bus
- **Real-time log streaming** via WebSocket
- **LLM cost tracking** with per-agent and per-model breakdowns

## Project Structure

```
sahayakan/
+-- control-plane/          # API server, event bus
|   +-- api-server/         # FastAPI application
|   +-- event_bus/          # Event processor
+-- data-plane/             # Agent execution engine
|   +-- agent_runner/       # Runner, contracts, knowledge cache
|   +-- agents/             # Issue triage, PR context, meeting summary
|   +-- llm_client/         # Gemini client (Vertex AI)
|   +-- prompts/            # Version-controlled prompt templates
+-- ingestion/              # GitHub and Jira data fetchers
+-- knowledge-cache/        # Git-based knowledge repository
+-- web-ui/                 # React + Material UI dashboard
+-- cli/                    # Command-line tool
+-- infrastructure/         # Docker Compose, migrations
+-- tests/                  # Unit, integration, e2e tests
+-- docs/                   # Architecture and stage plans
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API Server | Python, FastAPI |
| Frontend | React, Material UI, Vite |
| LLM | Vertex AI (Gemini) |
| Database | PostgreSQL |
| Blob Storage | MinIO |
| Knowledge Store | Git |
| Containers | Docker / Podman |

## Running Tests

```bash
# Unit tests
python3 tests/unit/test_sanitize.py
python3 tests/unit/test_knowledge_cache.py
python3 tests/unit/test_llm_client.py
python3 tests/unit/test_agent_contract.py

# E2E tests (requires running database)
python3 tests/test_issue_triage_e2e.py
python3 tests/test_stage5_e2e.py
```
