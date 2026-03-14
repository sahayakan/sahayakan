# Insights Agent

The Insights agent scans all previous agent analyses to detect recurring patterns, tech debt signals, and team dynamics.

## Input

No specific parameters required — it analyzes all existing reports in the knowledge cache.

## What It Does

1. Loads all existing agent outputs (issue analyses, PR contexts, meeting summaries)
2. Looks for patterns across multiple analyses
3. Uses the LLM to identify recurring themes
4. Produces an insights report

## Output

| Field | Description |
|-------|-------------|
| `recurring_patterns` | Issues and themes that appear repeatedly |
| `tech_debt_signals` | Code quality concerns surfaced across PR reviews |
| `team_dynamics` | Collaboration patterns and potential bottlenecks |
| `common_themes` | Frequently discussed topics |
| `recommendations` | Suggested actions based on detected patterns |

## Running

```bash
python3 -m cli.main run insights
```

!!! tip
    Run the Insights agent after accumulating several issue triage and PR context reports for the best results. It works best with 10+ analyses to draw from.

## Report Location

```
knowledge-cache/agent_outputs/insights/latest.json
knowledge-cache/agent_outputs/insights/latest.md
```
