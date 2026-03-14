# Insights Page

The Insights page shows patterns and trends detected by the Insights and Trend Analysis agents.

## Insights

The Insights agent scans all previous analyses to detect:

- **Recurring patterns** — Issues that keep appearing across analyses
- **Tech debt signals** — Code quality concerns mentioned in PR reviews
- **Team dynamics** — Collaboration patterns and bottlenecks
- **Common themes** — Frequently mentioned topics

## Trend Analysis

The Trend Analysis agent tracks metrics over time:

- **Project health score** — Overall project health (0-100)
- **Risk areas** — Categories with increasing problems
- **Velocity trends** — Issue/PR throughput changes
- **Recommendations** — Actionable suggestions based on trends

## Running Insights

Insights and trend analysis agents work best when run periodically after other agents have generated analyses. You can:

1. Run them manually from the [Agents page](agents.md)
2. Set up a [scheduled job](../integrations/github-app.md#webhooks) to run them automatically (e.g., daily)

```bash
# Run insights agent
python3 -m cli.main run insights

# Run trend analysis
python3 -m cli.main run trend-analysis
```
