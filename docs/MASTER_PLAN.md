# Sahayakan - Master Plan

## Vision

Sahayakan ("helper" in Sanskrit) is an autonomous agentic AI platform that assists software teams by analyzing development data and producing traceable reports. Agents run fully autonomously with optional human review at any stage, backed by a complete audit trail.

## Key Principles

1. **Autonomous by default** - Agents run without human intervention
2. **Human review optional at any stage** - Any step can be paused for review
3. **Complete audit trail** - Every action is traceable via Git commits, database records, and artifact references
4. **Control Plane / Data Plane separation** - Orchestration logic is cleanly separated from agent execution
5. **Event-driven architecture** - Agents communicate through events, not direct calls

## Technology Stack

| Layer              | Technology                |
| ------------------ | ------------------------- |
| Language           | Python                    |
| API Server         | FastAPI                   |
| Frontend           | React + Material UI       |
| LLM Backend        | Vertex AI (Gemini)        |
| Metadata DB        | PostgreSQL                |
| Blob Storage       | MinIO                     |
| Knowledge Store    | Git repository            |
| Log Streaming      | WebSocket                 |
| Containerization   | Docker + Docker Compose   |
| Deployment         | Linux VM                  |
| Data Sources (MVP) | GitHub, Jira              |

## MVP Agents

1. **Issue Triage Agent** - Analyzes GitHub issues for priority, duplicates, related PRs
2. **PR Context Agent** - Summarizes PRs, links Jira tickets, finds relevant discussions
3. **Meeting Summary Agent** - Extracts action items, decisions, and linked tasks from transcripts

## Architecture Overview

```
                    Users / API Clients
                           |
                           v
                +----- Control Plane -----+
                | FastAPI API Server      |
                | Job Scheduler           |
                | Event Bus (PostgreSQL)  |
                | Agent Registry          |
                | Review Gate System      |
                | Metadata DB (Postgres)  |
                +------------+------------+
                             |
                             v
                +------ Data Plane -------+
                | Agent Runner (Docker)   |
                | Issue Triage Agent      |
                | PR Context Agent        |
                | Meeting Summary Agent   |
                |                         |
                | Gemini (Vertex AI)      |
                | Knowledge Cache (Git)   |
                | Blob Storage (MinIO)    |
                +-------------------------+
```

## Monorepo Structure

```
sahayakan/
|
+-- docs/                        # Project documentation
|   +-- MASTER_PLAN.md
|   +-- stages/                  # Detailed stage plans
|
+-- control-plane/
|   +-- api-server/              # FastAPI application
|   +-- scheduler/               # Job scheduler
|   +-- event-bus/               # Event processing
|
+-- data-plane/
|   +-- agent-runner/            # Agent execution engine
|   +-- agents/
|   |   +-- issue-triage/
|   |   +-- pr-context/
|   |   +-- meeting-summary/
|   +-- llm-client/             # Shared Gemini client
|   +-- prompts/                # Version-controlled prompt templates
|
+-- knowledge-cache/            # Git-based knowledge repository
|   +-- github/
|   |   +-- issues/
|   |   +-- pull_requests/
|   +-- jira/
|   |   +-- tickets/
|   +-- meetings/
|   |   +-- transcripts/
|   +-- agent_outputs/
|       +-- issue_analysis/
|       +-- pr_context/
|       +-- meeting_summaries/
|
+-- ingestion/                  # Data ingestion services
|   +-- github-fetcher/
|   +-- jira-fetcher/
|
+-- web-ui/                     # React + Material UI frontend
|
+-- infrastructure/
|   +-- docker-compose.yml
|   +-- dockerfiles/
|   +-- db/
|       +-- migrations/
|
+-- cli/                        # Developer CLI tool
|
+-- tests/
    +-- unit/
    +-- integration/
    +-- e2e/
```

## Development Stages

The MVP is broken into **6 stages**, each building on the previous:

| Stage | Name                        | Description                                                |
| ----- | --------------------------- | ---------------------------------------------------------- |
| 1     | Foundation                  | Repo structure, Docker infra, PostgreSQL schema, FastAPI skeleton |
| 2     | Agent Runtime               | Agent execution contract, runner, Docker containers, LLM client |
| 3     | First Agent Pipeline        | Issue Triage Agent end-to-end with GitHub ingestion         |
| 4     | Observability & UI          | Log streaming, React dashboard, report viewer              |
| 5     | Remaining Agents & Events   | PR Context Agent, Meeting Summary Agent, Event Bus          |
| 6     | Stabilization & Polish      | Error handling, cost tracking, CLI tool, review gates, testing |

Each stage has a detailed plan in `docs/stages/`.

## Data Model (Core Entities)

```
Agent --> Job --> Agent Run --> Artifacts
                           --> LLM Usage
Event Bus connects everything
Review Gates pause execution for human approval (optional)
```

## Audit Trail Model

Every agent run produces:
1. **Git commit** in knowledge-cache with structured commit message
2. **Database records** in PostgreSQL (job, run, artifacts, LLM usage)
3. **Event record** for downstream processing
4. **Log archive** accessible via WebSocket and stored in MinIO

## Review Gate System

Agents run autonomously by default. At any stage, a review gate can be configured:

```
Agent starts
     |
     v
Data Collection --> [optional review gate]
     |
     v
LLM Analysis --> [optional review gate]
     |
     v
Report Generation --> [optional review gate]
     |
     v
Artifact Storage
     |
     v
Completion
```

Review gates are configured per-agent, per-stage via the API or UI.
When a gate is active, the job pauses with status `awaiting_review` until approved or rejected.
