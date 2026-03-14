from fastapi import APIRouter, HTTPException

from app.database import get_pool
from app.log_store import get_log_count, get_logs, get_logs_from_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{job_id}")
async def get_job_logs(job_id: int, offset: int = 0, limit: int = 100):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM jobs WHERE id = $1", job_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    logs = get_logs(job_id, offset=offset, limit=limit)
    total = get_log_count(job_id)

    # Fall back to DB if in-memory logs are empty
    if not logs:
        logs, total = await get_logs_from_db(pool, job_id, offset=offset, limit=limit)

    return {
        "job_id": job_id,
        "logs": logs,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.delete("/cleanup")
async def cleanup_logs(days: int = 30):
    """Delete job logs older than the specified number of days."""
    pool = await get_pool()
    result = await pool.execute(f"DELETE FROM job_logs WHERE created_at < NOW() - INTERVAL '{days} days'")
    deleted = int(result.split()[-1]) if result else 0
    return {"deleted": deleted, "retention_days": days}
