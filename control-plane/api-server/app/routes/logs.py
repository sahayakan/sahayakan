from fastapi import APIRouter, HTTPException

from app.database import get_pool

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{job_id}")
async def get_logs(job_id: int):
    """Retrieve logs for a job. Full implementation in Stage 4."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM jobs WHERE id = $1", job_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job_id": job_id, "logs": [], "message": "Log streaming available in Stage 4"}
