# Agents Overview

Agents are the core of Sahayakan. Each agent is a specialized pipeline that ingests data, analyzes it with an LLM, and produces structured reports.

## Available Agents

| Agent | Input | Output |
|-------|-------|--------|
| [Issue Triage](issue-triage.md) | GitHub issue | Priority, duplicates, related PRs, suggested labels |
| [PR Context](pr-context.md) | Pull request | Risk level, change type, review suggestions |
| [Meeting Summary](meeting-summary.md) | Meeting transcript | Action items, decisions, key topics |
| [Slack Digest](slack-digest.md) | Slack channel | Key discussions, decisions, action items |
| [Insights](insights.md) | All analyses | Recurring patterns, tech debt signals |
| [Trend Analysis](trend-analysis.md) | All metrics | Health score, risk areas, recommendations |

## Agent Lifecycle

Every agent follows a 5-step lifecycle:

```
load_input → collect_context → analyze → generate_output → store_artifacts
```

1. **load_input** — Validates input parameters and loads the target data
2. **collect_context** — Gathers related context from the knowledge cache (e.g., related issues, previous analyses)
3. **analyze** — Sends a structured prompt to the LLM and parses the response
4. **generate_output** — Produces a structured report (JSON + Markdown)
5. **store_artifacts** — Saves outputs to the knowledge cache with a Git commit

## Review Gates

Any step in the lifecycle can be paused for human review. When a review gate is active:

1. The job pauses with status `awaiting_review`
2. A reviewer inspects the intermediate output
3. The reviewer approves (continue) or rejects (stop) the job

Review gates are configured per-agent via the web dashboard or CLI.

## Running Agents

=== "Web Dashboard"

    Go to the **Agents** page and click **Run** on any agent.

=== "CLI"

    ```bash
    python3 -m cli.main run <agent-name> [options]
    ```

=== "API"

    ```bash
    curl -X POST http://localhost:8000/jobs/run \
      -H "Content-Type: application/json" \
      -d '{"agent": "<agent-name>", "parameters": {...}}'
    ```

## Audit Trail

Every agent run produces:

1. **Git commit** in the knowledge cache with a structured commit message
2. **Database records** — job, run status, artifacts, LLM usage
3. **Event** — published to the event bus for downstream processing
4. **Logs** — accessible via WebSocket and stored for review
