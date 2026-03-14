# Issue Triage Agent

The Issue Triage agent analyzes GitHub issues to determine priority, detect duplicates, and suggest labels.

## Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `issue_id` | string | GitHub issue number to analyze |

## What It Does

1. Loads the issue from the knowledge cache (must be synced first)
2. Gathers context: related issues, existing labels, past triage reports
3. Sends the issue content to the LLM with a structured prompt
4. Produces a triage report

## Output

The report includes:

| Field | Description |
|-------|-------------|
| `priority` | Suggested priority: `critical`, `high`, `medium`, `low` |
| `summary` | One-line summary of the issue |
| `suggested_labels` | Recommended labels to apply |
| `duplicates` | Potential duplicate issues |
| `related_prs` | Pull requests that may address this issue |
| `confidence` | Model confidence in the analysis |
| `llm_usage` | Token counts and latency |

## Running

```bash
# Sync issues first
python3 -m cli.main sync github myorg my-project

# Run triage on issue #42
python3 -m cli.main run issue-triage --issue 42

# View the report
python3 -m cli.main report view issue_analysis 42
```

## Report Location

Reports are stored in the knowledge cache at:

```
knowledge-cache/agent_outputs/issue_analysis/{issue_number}.json
knowledge-cache/agent_outputs/issue_analysis/{issue_number}.md
```
