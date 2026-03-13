"""Prometheus metrics for the Sahayakan platform.

Exposes key metrics at /metrics endpoint in Prometheus text format.
No external dependency required - generates text format directly.
"""

from app.database import get_pool


class MetricsCollector:
    """Collects metrics from the database for Prometheus exposition."""

    async def collect(self) -> str:
        pool = await get_pool()
        lines = []
        lines.append("# Sahayakan Metrics")
        lines.append("")

        # Job metrics
        rows = await pool.fetch("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
        lines.append("# HELP sahayakan_jobs_total Total jobs by status")
        lines.append("# TYPE sahayakan_jobs_total gauge")
        for r in rows:
            lines.append(f'sahayakan_jobs_total{{status="{r["status"]}"}} {r["count"]}')

        # Agent run metrics
        rows = await pool.fetch(
            "SELECT agent_name, status, COUNT(*) as count FROM agent_runs GROUP BY agent_name, status"
        )
        lines.append("")
        lines.append("# HELP sahayakan_agent_runs_total Agent runs by agent and status")
        lines.append("# TYPE sahayakan_agent_runs_total gauge")
        for r in rows:
            lines.append(f'sahayakan_agent_runs_total{{agent="{r["agent_name"]}",status="{r["status"]}"}} {r["count"]}')

        # Agent execution time
        rows = await pool.fetch(
            "SELECT agent_name, "
            "AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_seconds, "
            "MAX(EXTRACT(EPOCH FROM (end_time - start_time))) as max_seconds, "
            "COUNT(*) as count "
            "FROM agent_runs WHERE end_time IS NOT NULL "
            "GROUP BY agent_name"
        )
        lines.append("")
        lines.append("# HELP sahayakan_agent_duration_seconds Agent execution duration")
        lines.append("# TYPE sahayakan_agent_duration_seconds gauge")
        for r in rows:
            if r["avg_seconds"] is not None:
                lines.append(
                    f'sahayakan_agent_duration_seconds{{agent="{r["agent_name"]}",quantile="avg"}} {r["avg_seconds"]:.3f}'
                )
                lines.append(
                    f'sahayakan_agent_duration_seconds{{agent="{r["agent_name"]}",quantile="max"}} {r["max_seconds"]:.3f}'
                )

        # LLM usage
        rows = await pool.fetch(
            "SELECT model, COUNT(*) as calls, "
            "SUM(tokens_input) as tokens_in, SUM(tokens_output) as tokens_out, "
            "AVG(latency_ms) as avg_latency "
            "FROM llm_usage GROUP BY model"
        )
        lines.append("")
        lines.append("# HELP sahayakan_llm_calls_total LLM API calls by model")
        lines.append("# TYPE sahayakan_llm_calls_total counter")
        for r in rows:
            lines.append(f'sahayakan_llm_calls_total{{model="{r["model"]}"}} {r["calls"]}')

        lines.append("")
        lines.append("# HELP sahayakan_llm_tokens_total Total tokens processed")
        lines.append("# TYPE sahayakan_llm_tokens_total counter")
        for r in rows:
            lines.append(f'sahayakan_llm_tokens_total{{model="{r["model"]}",direction="input"}} {r["tokens_in"]}')
            lines.append(f'sahayakan_llm_tokens_total{{model="{r["model"]}",direction="output"}} {r["tokens_out"]}')

        lines.append("")
        lines.append("# HELP sahayakan_llm_latency_ms LLM average latency in milliseconds")
        lines.append("# TYPE sahayakan_llm_latency_ms gauge")
        for r in rows:
            if r["avg_latency"] is not None:
                lines.append(f'sahayakan_llm_latency_ms{{model="{r["model"]}"}} {r["avg_latency"]:.0f}')

        # Event bus metrics
        unprocessed = await pool.fetchval("SELECT COUNT(*) FROM events WHERE processed = FALSE")
        total_events = await pool.fetchval("SELECT COUNT(*) FROM events")
        lines.append("")
        lines.append("# HELP sahayakan_events_total Total events")
        lines.append("# TYPE sahayakan_events_total counter")
        lines.append(f"sahayakan_events_total {total_events}")
        lines.append("")
        lines.append("# HELP sahayakan_events_unprocessed Unprocessed events (lag)")
        lines.append("# TYPE sahayakan_events_unprocessed gauge")
        lines.append(f"sahayakan_events_unprocessed {unprocessed}")

        # Insights
        active_insights = await pool.fetchval("SELECT COUNT(*) FROM insights WHERE status = 'active'")
        lines.append("")
        lines.append("# HELP sahayakan_insights_active Active insights count")
        lines.append("# TYPE sahayakan_insights_active gauge")
        lines.append(f"sahayakan_insights_active {active_insights}")

        # Embeddings
        try:
            embedding_count = await pool.fetchval("SELECT COUNT(*) FROM embeddings")
            lines.append("")
            lines.append("# HELP sahayakan_embeddings_total Total embeddings")
            lines.append("# TYPE sahayakan_embeddings_total gauge")
            lines.append(f"sahayakan_embeddings_total {embedding_count}")
        except Exception:
            pass

        lines.append("")
        return "\n".join(lines)


metrics_collector = MetricsCollector()
