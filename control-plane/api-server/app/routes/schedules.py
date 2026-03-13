"""Schedule management API endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.database import get_pool

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    name: str
    agent_name: str | None = None
    schedule_type: str = "agent_job"  # agent_job, github_sync, jira_sync, slack_sync
    cron_expression: str
    parameters: dict[str, Any] = {}
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None


@router.get("")
async def list_schedules():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, name, agent_name, schedule_type, cron_expression, "
        "parameters, enabled, last_run_at, next_run_at, created_at "
        "FROM schedules ORDER BY created_at"
    )
    return {"schedules": [dict(r) for r in rows]}


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM schedules WHERE id = $1", schedule_id
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return dict(row)


@router.post("", status_code=201)
async def create_schedule(schedule: ScheduleCreate):
    pool = await get_pool()

    # Validate agent exists if agent_job type
    if schedule.schedule_type == "agent_job":
        if not schedule.agent_name:
            raise HTTPException(status_code=400, detail="agent_name required for agent_job schedules")
        agent = await pool.fetchrow(
            "SELECT name FROM agents WHERE name = $1", schedule.agent_name
        )
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{schedule.agent_name}' not found")

    # Validate cron expression (basic check)
    parts = schedule.cron_expression.strip().split()
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail="Cron expression must have 5 fields: minute hour day month weekday")
    next_run = None  # Will be computed by the scheduler service

    row = await pool.fetchrow(
        "INSERT INTO schedules "
        "(name, agent_name, schedule_type, cron_expression, parameters, enabled, next_run_at) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7) RETURNING *",
        schedule.name,
        schedule.agent_name,
        schedule.schedule_type,
        schedule.cron_expression,
        json.dumps(schedule.parameters),
        schedule.enabled,
        next_run,
    )
    return dict(row)


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, update: ScheduleUpdate):
    pool = await get_pool()

    existing = await pool.fetchrow("SELECT * FROM schedules WHERE id = $1", schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    updates = []
    args = [schedule_id]
    idx = 2

    if update.name is not None:
        updates.append(f"name = ${idx}")
        args.append(update.name)
        idx += 1
    if update.cron_expression is not None:
        updates.append(f"cron_expression = ${idx}")
        args.append(update.cron_expression)
        idx += 1
        # Reset next_run_at so scheduler service recomputes it
        updates.append(f"next_run_at = ${idx}")
        args.append(None)
        idx += 1
    if update.parameters is not None:
        updates.append(f"parameters = ${idx}::jsonb")
        args.append(json.dumps(update.parameters))
        idx += 1
    if update.enabled is not None:
        updates.append(f"enabled = ${idx}")
        args.append(update.enabled)
        idx += 1

    if not updates:
        return dict(existing)

    query = f"UPDATE schedules SET {', '.join(updates)} WHERE id = $1 RETURNING *"
    row = await pool.fetchrow(query, *args)
    return dict(row)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    pool = await get_pool()
    result = await pool.execute("DELETE FROM schedules WHERE id = $1", schedule_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return {"deleted": True}
