"""Insights API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightStatusUpdate(BaseModel):
    status: str  # 'active', 'acknowledged', 'resolved'


@router.get("")
async def list_insights(
    insight_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
):
    pool = await get_pool()
    query = "SELECT * FROM insights"
    conditions = []
    args = []
    idx = 1

    if insight_type:
        conditions.append(f"insight_type = ${idx}")
        args.append(insight_type)
        idx += 1
    if severity:
        conditions.append(f"severity = ${idx}")
        args.append(severity)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        args.append(status)
        idx += 1

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += f" ORDER BY created_at DESC LIMIT ${idx}"
    args.append(limit)

    rows = await pool.fetch(query, *args)
    return {"insights": [dict(r) for r in rows]}


@router.get("/summary")
async def insights_summary():
    pool = await get_pool()
    total = await pool.fetchval("SELECT COUNT(*) FROM insights")
    by_severity = await pool.fetch(
        "SELECT severity, COUNT(*) as count FROM insights WHERE status = 'active' GROUP BY severity"
    )
    by_type = await pool.fetch(
        "SELECT insight_type, COUNT(*) as count FROM insights WHERE status = 'active' GROUP BY insight_type"
    )
    return {
        "total": total,
        "active_by_severity": {r["severity"]: r["count"] for r in by_severity},
        "active_by_type": {r["insight_type"]: r["count"] for r in by_type},
    }


@router.get("/trends")
async def get_trends():
    """Return trend data for dashboard charts."""
    pool = await get_pool()

    # Job completion trends (last 30 days)
    job_trends = await pool.fetch(
        "SELECT DATE(created_at) as day, status, COUNT(*) as count "
        "FROM jobs GROUP BY DATE(created_at), status "
        "ORDER BY day DESC LIMIT 200"
    )

    # LLM usage trends
    usage_trends = await pool.fetch(
        "SELECT DATE(created_at) as day, "
        "SUM(tokens_input) as tokens_in, SUM(tokens_output) as tokens_out, "
        "COUNT(*) as calls "
        "FROM llm_usage GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30"
    )

    # Event volume
    event_trends = await pool.fetch(
        "SELECT DATE(created_at) as day, event_type, COUNT(*) as count "
        "FROM events GROUP BY DATE(created_at), event_type "
        "ORDER BY day DESC LIMIT 200"
    )

    return {
        "job_trends": [{"day": str(r["day"]), "status": r["status"], "count": r["count"]} for r in job_trends],
        "usage_trends": [
            {"day": str(r["day"]), "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"], "calls": r["calls"]}
            for r in usage_trends
        ],
        "event_trends": [
            {"day": str(r["day"]), "event_type": r["event_type"], "count": r["count"]} for r in event_trends
        ],
    }


@router.get("/{insight_id}")
async def get_insight(insight_id: int):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM insights WHERE id = $1", insight_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Insight {insight_id} not found")
    return dict(row)


@router.put("/{insight_id}/status")
async def update_insight_status(insight_id: int, update: InsightStatusUpdate):
    if update.status not in ("active", "acknowledged", "resolved"):
        raise HTTPException(status_code=400, detail="Status must be active, acknowledged, or resolved")
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE insights SET status = $2, updated_at = NOW() WHERE id = $1 RETURNING *",
        insight_id,
        update.status,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Insight {insight_id} not found")
    return dict(row)
