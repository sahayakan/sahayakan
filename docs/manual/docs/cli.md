# CLI Reference

The Sahayakan CLI provides command-line access to all platform features.

## Usage

```bash
python3 -m cli.main <command> [options]
```

## System Commands

### `status`
Show system health.

```bash
python3 -m cli.main status
# Status:   healthy
# Database: connected
# Version:  0.1.0
```

### `usage`
Show LLM usage summary.

```bash
python3 -m cli.main usage
# Total runs:      42
# Total tokens in: 125,000
# Total tokens out:18,500
# Estimated cost:  $0.1234
```

## Agent Commands

### `agent list`
List all registered agents.

```bash
python3 -m cli.main agent list
```

### `agent info <name>`
Show agent details.

```bash
python3 -m cli.main agent info issue-triage
```

### `agent gates <name>`
Show or configure review gates.

```bash
# View gates
python3 -m cli.main agent gates issue-triage

# Enable a gate
python3 -m cli.main agent gates issue-triage --set analyze=true

# Disable a gate
python3 -m cli.main agent gates issue-triage --set analyze=false
```

## Run Command

### `run <agent-name>`
Run an agent with parameters.

```bash
# Run Issue Triage
python3 -m cli.main run issue-triage --issue 42

# Run PR Context
python3 -m cli.main run pr-context --pr 10

# Run Meeting Summary
python3 -m cli.main run meeting-summary --transcript meeting-2024-01-15

# Run with custom parameters
python3 -m cli.main run slack-digest --param channel_name=engineering
```

## Job Commands

### `job list`
List jobs with optional filters.

```bash
python3 -m cli.main job list
python3 -m cli.main job list --status completed --limit 10
```

### `job status <id>`
Show job details.

```bash
python3 -m cli.main job status 42
```

### `job logs <id>`
Show job logs.

```bash
python3 -m cli.main job logs 42 --limit 200
```

### `job review <id>`
Submit a review decision for a paused job.

```bash
# Approve
python3 -m cli.main job review 42 --approve --comment "Looks good"

# Reject
python3 -m cli.main job review 42 --reject "Analysis is incorrect"
```

## Sync Commands

### `sync github <owner> <repo>`
Trigger GitHub data ingestion.

```bash
python3 -m cli.main sync github myorg my-project
```

### `sync status`
Show ingestion status.

```bash
python3 -m cli.main sync status
# GitHub issues cached:  45
# GitHub PRs cached:     23
# Jira tickets cached:   12
```

## Report Commands

### `report list`
List generated reports.

```bash
python3 -m cli.main report list
python3 -m cli.main report list --type issue_analysis
```

### `report view <type> <id>`
View a report.

```bash
# Markdown view (default)
python3 -m cli.main report view issue_analysis 42

# Raw JSON
python3 -m cli.main report view issue_analysis 42 --json
```

## Events Commands

### `events list`
List recent events.

```bash
python3 -m cli.main events list --limit 20
python3 -m cli.main events list --type job.completed
```

## Knowledge Commands

### `knowledge search <query>`
Semantic search across the knowledge base.

```bash
python3 -m cli.main knowledge search "authentication failures"
python3 -m cli.main knowledge search "database issues" --type issue --type pr --limit 5
```

### `knowledge stats`
Show embedding statistics.

```bash
python3 -m cli.main knowledge stats
```

## Schedule Commands

### `schedule list`
List all schedules.

```bash
python3 -m cli.main schedule list
```

### `schedule create <name>`
Create a new schedule.

```bash
python3 -m cli.main schedule create daily-triage \
  --agent issue-triage \
  --cron "0 9 * * *" \
  --param issue_id=latest
```

### `schedule toggle <id>`
Enable or disable a schedule.

```bash
python3 -m cli.main schedule toggle 1 --enable
python3 -m cli.main schedule toggle 1 --disable
```

### `schedule delete <id>`
Delete a schedule.

```bash
python3 -m cli.main schedule delete 1
```
