import json

from fastapi import APIRouter, HTTPException

from app.database import get_pool
from app.models.jobs import JobCreate, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreate):
    pool = await get_pool()

    # Verify agent exists
    agent = await pool.fetchrow("SELECT name FROM agents WHERE name = $1", job.agent)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{job.agent}' not found. Register the agent first.",
        )

    row = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) "
        "VALUES ($1, 'pending', $2::jsonb) "
        "RETURNING id, agent_name, status, parameters, "
        "created_at, started_at, completed_at",
        job.agent,
        json.dumps(job.parameters),
    )
    result = dict(row)
    if isinstance(result["parameters"], str):
        result["parameters"] = json.loads(result["parameters"])
    return result


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    status: str | None = None,
    agent: str | None = None,
    limit: int = 50,
):
    pool = await get_pool()

    query = "SELECT id, agent_name, status, parameters, created_at, started_at, completed_at FROM jobs"
    conditions = []
    args = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}::job_status")
        args.append(status)
        idx += 1
    if agent:
        conditions.append(f"agent_name = ${idx}")
        args.append(agent)
        idx += 1

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY created_at DESC LIMIT ${idx}"
    args.append(limit)

    rows = await pool.fetch(query, *args)
    results = []
    for row in rows:
        r = dict(row)
        if isinstance(r["parameters"], str):
            r["parameters"] = json.loads(r["parameters"])
        results.append(r)
    return results


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, agent_name, status, parameters, created_at, started_at, completed_at FROM jobs WHERE id = $1",
        job_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    result = dict(row)
    if isinstance(result["parameters"], str):
        result["parameters"] = json.loads(result["parameters"])
    return result


@router.get("/{job_id}/runs")
async def get_job_runs(job_id: int):
    """Get agent runs for a job, including artifacts and LLM usage."""
    pool = await get_pool()

    # Verify job exists
    job = await pool.fetchrow("SELECT id FROM jobs WHERE id = $1", job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    runs = await pool.fetch(
        "SELECT id, job_id, agent_name, status, start_time, end_time, git_commit, logs_uri "
        "FROM agent_runs WHERE job_id = $1 ORDER BY start_time DESC",
        job_id,
    )

    results = []
    for run in runs:
        run_dict = dict(run)
        run_id = run["id"]

        # Fetch artifacts for this run
        artifacts = await pool.fetch(
            "SELECT id, artifact_type, storage_uri, metadata, created_at "
            "FROM artifacts WHERE run_id = $1 ORDER BY created_at",
            run_id,
        )
        run_dict["artifacts"] = []
        for a in artifacts:
            ad = dict(a)
            if isinstance(ad.get("metadata"), str):
                ad["metadata"] = json.loads(ad["metadata"])
            run_dict["artifacts"].append(ad)

        # Fetch LLM usage for this run
        usage_rows = await pool.fetch(
            "SELECT id, model, tokens_input, tokens_output, latency_ms, estimated_cost, created_at "
            "FROM llm_usage WHERE run_id = $1 ORDER BY created_at",
            run_id,
        )
        run_dict["llm_usage"] = [dict(u) for u in usage_rows]

        results.append(run_dict)

    return {"job_id": job_id, "runs": results}
