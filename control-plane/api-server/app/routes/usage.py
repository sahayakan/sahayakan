"""LLM usage and cost tracking API."""

from fastapi import APIRouter

from app.database import get_pool

router = APIRouter(prefix="/usage", tags=["usage"])

# Pricing per 1K tokens (update as needed)
MODEL_PRICING = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "mock-model": {"input": 0.0, "output": 0.0},
}


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.001, "output": 0.004})
    return (tokens_in / 1000 * pricing["input"]) + (tokens_out / 1000 * pricing["output"])


@router.get("/summary")
async def usage_summary():
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT COUNT(*) as total_runs, "
        "COALESCE(SUM(tokens_input), 0) as total_tokens_input, "
        "COALESCE(SUM(tokens_output), 0) as total_tokens_output, "
        "COALESCE(SUM(latency_ms), 0) as total_latency_ms "
        "FROM llm_usage"
    )
    total_cost = 0.0
    rows = await pool.fetch("SELECT model, tokens_input, tokens_output FROM llm_usage")
    for r in rows:
        total_cost += _estimate_cost(r["model"], r["tokens_input"] or 0, r["tokens_output"] or 0)

    return {
        "total_runs": row["total_runs"],
        "total_tokens_input": row["total_tokens_input"],
        "total_tokens_output": row["total_tokens_output"],
        "total_latency_ms": row["total_latency_ms"],
        "total_estimated_cost": round(total_cost, 6),
    }


@router.get("/by-agent")
async def usage_by_agent():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT r.agent_name, COUNT(*) as runs, "
        "COALESCE(SUM(u.tokens_input), 0) as tokens_input, "
        "COALESCE(SUM(u.tokens_output), 0) as tokens_output, "
        "COALESCE(AVG(u.latency_ms), 0) as avg_latency_ms "
        "FROM llm_usage u JOIN agent_runs r ON u.run_id = r.id "
        "GROUP BY r.agent_name ORDER BY runs DESC"
    )
    results = []
    for r in rows:
        cost = _estimate_cost("gemini-1.5-pro", r["tokens_input"], r["tokens_output"])
        results.append({
            "agent": r["agent_name"], "runs": r["runs"],
            "tokens_input": r["tokens_input"], "tokens_output": r["tokens_output"],
            "avg_latency_ms": round(r["avg_latency_ms"]), "estimated_cost": round(cost, 6),
        })
    return {"agents": results}


@router.get("/by-model")
async def usage_by_model():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT model, COUNT(*) as calls, "
        "COALESCE(SUM(tokens_input), 0) as tokens_input, "
        "COALESCE(SUM(tokens_output), 0) as tokens_output "
        "FROM llm_usage GROUP BY model ORDER BY calls DESC"
    )
    results = []
    for r in rows:
        cost = _estimate_cost(r["model"], r["tokens_input"], r["tokens_output"])
        results.append({
            "model": r["model"], "calls": r["calls"],
            "tokens_input": r["tokens_input"], "tokens_output": r["tokens_output"],
            "estimated_cost": round(cost, 6),
        })
    return {"models": results}


@router.get("/daily")
async def usage_daily():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT DATE(created_at) as day, COUNT(*) as calls, "
        "COALESCE(SUM(tokens_input), 0) as tokens_input, "
        "COALESCE(SUM(tokens_output), 0) as tokens_output "
        "FROM llm_usage GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30"
    )
    return {"daily": [{"day": str(r["day"]), "calls": r["calls"],
                        "tokens_input": r["tokens_input"], "tokens_output": r["tokens_output"]} for r in rows]}
