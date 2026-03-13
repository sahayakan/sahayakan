import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(tags=["reviews"])


class ReviewDecision(BaseModel):
    decision: str  # "approved" or "rejected"
    reviewer: str | None = None
    comments: str | None = None


class GateConfig(BaseModel):
    stage: str
    enabled: bool


class GateResponse(BaseModel):
    agent_name: str
    stage: str
    enabled: bool


# --- Review endpoints ---


@router.post("/jobs/{job_id}/review", status_code=201)
async def submit_review(job_id: int, review: ReviewDecision):
    if review.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'",
        )

    pool = await get_pool()

    # Find the active run for this job
    run = await pool.fetchrow(
        "SELECT id, status FROM agent_runs "
        "WHERE job_id = $1 AND status = 'awaiting_review' "
        "ORDER BY start_time DESC LIMIT 1",
        job_id,
    )
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"No run awaiting review for job {job_id}",
        )

    # Find which stage is awaiting review (most recent gate log)
    # We store the stage from the review_gates check
    job = await pool.fetchrow("SELECT agent_name FROM jobs WHERE id = $1", job_id)
    gates = await pool.fetch(
        "SELECT stage FROM review_gates WHERE agent_name = $1 AND enabled = true",
        job["agent_name"],
    )
    # Find the stage that doesn't have a decision yet
    stage = None
    for gate in gates:
        existing = await pool.fetchrow(
            "SELECT id FROM review_decisions "
            "WHERE run_id = $1 AND stage = $2",
            run["id"],
            gate["stage"],
        )
        if not existing:
            stage = gate["stage"]
            break

    if not stage:
        raise HTTPException(
            status_code=400,
            detail="Could not determine which stage needs review",
        )

    await pool.execute(
        "INSERT INTO review_decisions (run_id, stage, decision, reviewer, comments) "
        "VALUES ($1, $2, $3, $4, $5)",
        run["id"],
        stage,
        review.decision,
        review.reviewer,
        review.comments,
    )

    return {
        "job_id": job_id,
        "run_id": run["id"],
        "stage": stage,
        "decision": review.decision,
    }


@router.get("/jobs/{job_id}/review-status")
async def get_review_status(job_id: int):
    pool = await get_pool()

    job = await pool.fetchrow(
        "SELECT id, status, agent_name FROM jobs WHERE id = $1", job_id
    )
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    run = await pool.fetchrow(
        "SELECT id, status FROM agent_runs "
        "WHERE job_id = $1 ORDER BY start_time DESC LIMIT 1",
        job_id,
    )

    decisions = []
    if run:
        rows = await pool.fetch(
            "SELECT stage, decision, reviewer, comments, decided_at "
            "FROM review_decisions WHERE run_id = $1 ORDER BY decided_at",
            run["id"],
        )
        decisions = [dict(r) for r in rows]

    return {
        "job_id": job_id,
        "job_status": job["status"],
        "awaiting_review": job["status"] == "awaiting_review",
        "decisions": decisions,
    }


# --- Gate configuration endpoints ---


@router.get("/agents/{name}/gates", response_model=list[GateResponse])
async def list_gates(name: str):
    pool = await get_pool()

    agent = await pool.fetchrow("SELECT name FROM agents WHERE name = $1", name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    rows = await pool.fetch(
        "SELECT agent_name, stage, enabled FROM review_gates "
        "WHERE agent_name = $1 ORDER BY stage",
        name,
    )
    return [dict(r) for r in rows]


@router.put("/agents/{name}/gates", response_model=list[GateResponse])
async def configure_gates(name: str, gates: list[GateConfig]):
    pool = await get_pool()

    agent = await pool.fetchrow("SELECT name FROM agents WHERE name = $1", name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    valid_stages = {"after_input", "after_context", "after_analysis", "after_output"}
    for gate in gates:
        if gate.stage not in valid_stages:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{gate.stage}'. Must be one of: {valid_stages}",
            )

    results = []
    for gate in gates:
        await pool.execute(
            "INSERT INTO review_gates (agent_name, stage, enabled) "
            "VALUES ($1, $2, $3) "
            "ON CONFLICT (agent_name, stage) DO UPDATE SET enabled = $3",
            name,
            gate.stage,
            gate.enabled,
        )
        results.append(
            {"agent_name": name, "stage": gate.stage, "enabled": gate.enabled}
        )

    return results
