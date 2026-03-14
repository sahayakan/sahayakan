# Web Dashboard Overview

The Sahayakan web dashboard is a React application that provides a visual interface for managing agents, monitoring jobs, viewing reports, and configuring integrations.

**URL**: `http://localhost:3000` (local) or `https://your-domain.com` (production)

## Navigation

The sidebar provides access to all pages:

| Page | Description |
|------|-------------|
| **Dashboard** | System overview with agent status and recent activity |
| **Agents** | View registered agents, run them, configure review gates |
| **Jobs** | Monitor running and completed jobs with real-time logs |
| **Reports** | Browse generated analysis reports |
| **Insights** | View detected patterns and trend analyses |
| **Search** | Semantic search across the knowledge base |
| **Events** | Browse the event log |
| **Settings** | Manage repositories, Jira projects, and GitHub App |

## Real-Time Updates

The dashboard polls the API at regular intervals to show updated data. Job logs stream in real-time via WebSocket connections.

## Authentication

In production, the dashboard is protected by:

1. **Caddy basic auth** — gates the entire site
2. **API key auth** — the dashboard passes API keys for backend requests

In development, set `AUTH_ENABLED=false` in your `.env` to bypass authentication.
