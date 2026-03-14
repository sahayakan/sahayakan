# Trend Analysis Agent

The Trend Analysis agent tracks project health metrics over time and highlights risk areas.

## Input

No specific parameters required — it analyzes all existing data and metrics.

## What It Does

1. Loads historical agent outputs, job metrics, and event data
2. Calculates trends across time periods
3. Uses the LLM to interpret trends and assess project health
4. Produces a trend report with a health score

## Output

| Field | Description |
|-------|-------------|
| `health_score` | Overall project health (0-100) |
| `risk_areas` | Categories with increasing problems |
| `velocity_trends` | Issue/PR throughput changes |
| `quality_trends` | Code quality and review metrics over time |
| `recommendations` | Actionable suggestions based on trends |

## Running

```bash
python3 -m cli.main run trend-analysis
```

!!! tip
    Schedule trend analysis to run periodically (e.g., weekly) to track changes over time. Use the **Schedules** feature to automate this.

    ```bash
    python3 -m cli.main schedule create weekly-trends \
      --agent trend-analysis \
      --cron "0 9 * * 1"
    ```

## Report Location

```
knowledge-cache/agent_outputs/trend_analysis/latest.json
knowledge-cache/agent_outputs/trend_analysis/latest.md
```
