"""Event management API endpoints."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.database import get_pool

router = APIRouter(prefix="/events", tags=["events"])


class EventPublish(BaseModel):
    event_type: str
    source: str
    payload: dict[str, Any] = {}


class SubscriptionCreate(BaseModel):
    event_type: str


@router.get("")
async def list_events(
    event_type: str | None = None,
    processed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    pool = await get_pool()
    query = "SELECT id, event_type, source, payload, created_at, processed FROM events"
    conditions = []
    args = []
    idx = 1

    if event_type:
        conditions.append(f"event_type = ${idx}")
        args.append(event_type)
        idx += 1
    if processed is not None:
        conditions.append(f"processed = ${idx}")
        args.append(processed)
        idx += 1

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    args.extend([limit, offset])

    rows = await pool.fetch(query, *args)
    return {"events": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.get("/types")
async def list_event_types():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT DISTINCT event_type, COUNT(*) as count "
        "FROM events GROUP BY event_type ORDER BY event_type"
    )
    return {"types": [{"event_type": r["event_type"], "count": r["count"]} for r in rows]}


@router.get("/{event_id}")
async def get_event(event_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, event_type, source, payload, created_at, processed "
        "FROM events WHERE id = $1",
        event_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return dict(row)


@router.post("/publish", status_code=201)
async def publish_event(event: EventPublish):
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO events (event_type, source, payload) "
        "VALUES ($1, $2, $3::jsonb) RETURNING id, created_at",
        event.event_type,
        event.source,
        json.dumps(event.payload),
    )
    return {"id": row["id"], "event_type": event.event_type, "created_at": row["created_at"]}


# --- Subscription endpoints ---

@router.get("/subscriptions/{agent_name}")
async def list_subscriptions(agent_name: str):
    pool = await get_pool()
    agent = await pool.fetchrow("SELECT name FROM agents WHERE name = $1", agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    rows = await pool.fetch(
        "SELECT agent_name, event_type FROM agent_subscriptions WHERE agent_name = $1",
        agent_name,
    )
    return {"subscriptions": [dict(r) for r in rows]}


@router.post("/subscriptions/{agent_name}", status_code=201)
async def add_subscription(agent_name: str, sub: SubscriptionCreate):
    pool = await get_pool()
    agent = await pool.fetchrow("SELECT name FROM agents WHERE name = $1", agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    try:
        await pool.execute(
            "INSERT INTO agent_subscriptions (agent_name, event_type) VALUES ($1, $2)",
            agent_name,
            sub.event_type,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Subscription already exists")
        raise
    return {"agent_name": agent_name, "event_type": sub.event_type}


@router.delete("/subscriptions/{agent_name}/{event_type}")
async def remove_subscription(agent_name: str, event_type: str):
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM agent_subscriptions WHERE agent_name = $1 AND event_type = $2",
        agent_name,
        event_type,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"deleted": True}
