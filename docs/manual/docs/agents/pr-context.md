# PR Context Agent

The PR Context agent analyzes pull requests to assess risk, summarize changes, and provide review guidance.

## Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `pr_number` | string | Pull request number to analyze |

## What It Does

1. Loads the PR from the knowledge cache
2. Gathers context: linked issues, existing issue triage reports, related PRs
3. Sends the PR content and context to the LLM
4. Produces a context report for reviewers

## Output

| Field | Description |
|-------|-------------|
| `change_type` | Category: `feature`, `bugfix`, `refactor`, `docs`, `test`, etc. |
| `risk_level` | Assessment: `low`, `medium`, `high`, `critical` |
| `summary` | Concise description of the changes |
| `breaking_changes` | Whether the PR introduces breaking changes |
| `linked_issues` | Related GitHub issues |
| `review_suggestions` | Specific areas reviewers should focus on |
| `confidence` | Model confidence in the analysis |

## Running

```bash
# Sync PRs first
python3 -m cli.main sync github myorg my-project

# Run PR context on PR #10
python3 -m cli.main run pr-context --pr 10

# View the report
python3 -m cli.main report view pr_context 10
```

!!! tip
    For best results, run Issue Triage first on related issues. The PR Context agent uses triage reports to enrich its analysis.

## Report Location

```
knowledge-cache/agent_outputs/pr_context/{pr_number}.json
knowledge-cache/agent_outputs/pr_context/{pr_number}.md
```
