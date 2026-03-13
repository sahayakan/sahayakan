import json

from app.database import get_pool


async def update_job_status(
    job_id: int,
    status: str,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict | None:
    pool = await get_pool()
    updates = ["status = $2::job_status"]
    args: list = [job_id, status]
    idx = 3

    if started_at:
        updates.append(f"started_at = ${idx}::timestamp")
        args.append(started_at)
        idx += 1
    if completed_at:
        updates.append(f"completed_at = ${idx}::timestamp")
        args.append(completed_at)
        idx += 1

    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = $1 RETURNING *"
    row = await pool.fetchrow(query, *args)
    return dict(row) if row else None


async def get_pending_jobs(limit: int = 10) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, agent_name, status, parameters, created_at "
        "FROM jobs WHERE status = 'pending' "
        "ORDER BY created_at ASC LIMIT $1",
        limit,
    )
    return [dict(row) for row in rows]
