# Prerequisites

Before installing Sahayakan, ensure you have the following:

## Required

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** or **Podman** | 20+ | Container runtime for all services |
| **Docker Compose** | v2+ | Multi-container orchestration |
| **Python** | 3.12+ | API server, agents, CLI |
| **Node.js** | 20+ | Web UI development |
| **Git** | 2.x | Knowledge cache version control |

## Optional

| Tool | Purpose |
|------|---------|
| **GitHub CLI** (`gh`) | Convenient authentication for test scripts |
| **Google Cloud SDK** | Required if using Vertex AI for LLM |

## External Services

Sahayakan integrates with external services. You'll need credentials for the ones you plan to use:

| Service | Required? | What You Need |
|---------|-----------|---------------|
| **GitHub App** | Yes (for GitHub sync) | App ID, private key, installation ID |
| **Gemini API** | Yes (for agent analysis) | `GEMINI_API_KEY` |
| **Jira** | Optional | URL, email, API token |
| **Slack** | Optional | Bot token with channel read permissions |

!!! note
    Sahayakan uses **GitHub App** authentication (not personal access tokens) for all GitHub connectivity. See [GitHub App Integration](../integrations/github-app.md) for setup instructions.
