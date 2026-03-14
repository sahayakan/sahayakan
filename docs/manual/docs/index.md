# Sahayakan User Manual

**Sahayakan** ("helper" in Sanskrit) is an autonomous agentic AI platform for software development teams. It analyzes GitHub issues, pull requests, meeting transcripts, and Slack conversations to produce traceable reports — with optional human review at any stage.

## What Sahayakan Does

Sahayakan runs a set of specialized **agents** that automatically process your development data:

- **Issue Triage** — Prioritizes GitHub issues, detects duplicates, and suggests labels
- **PR Context** — Summarizes pull requests, assesses risk, and links related issues
- **Meeting Summary** — Extracts action items and decisions from transcripts
- **Slack Digest** — Distills key discussions from Slack channels
- **Insights** — Detects recurring patterns and tech debt signals across all analyses
- **Trend Analysis** — Tracks project health trends and highlights risk areas

## Key Features

- **Autonomous execution** with optional human review gates at any stage
- **Complete audit trail** — every action produces a Git commit, database record, and event
- **Event-driven orchestration** — agents trigger each other through an event bus
- **Semantic search** across the knowledge base via pgvector embeddings
- **Scheduled automation** — cron-based scheduling and GitHub webhook triggers
- **Web dashboard** for monitoring agents, jobs, reports, and insights
- **CLI** for command-line workflows
- **API keys with RBAC** — scoped permissions and audit logging

## How to Use This Manual

- **[Getting Started](getting-started/prerequisites.md)** — Install and run Sahayakan locally
- **[Web Dashboard](dashboard/overview.md)** — Learn the dashboard UI
- **[Agents](agents/overview.md)** — Understand what each agent does and how to run it
- **[Integrations](integrations/github-app.md)** — Connect GitHub, Jira, and Slack
- **[CLI Reference](cli.md)** — Full command-line reference
- **[API Reference](api.md)** — REST API endpoints
- **[Architecture](architecture.md)** — System design and data flow
