from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth import AuthContext, get_auth_context, log_audit
from app.database import get_pool
from app.models.agents import AgentRegister, AgentResponse

CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, name, version, description, container_image, "
        "created_at, updated_at FROM agents ORDER BY created_at DESC"
    )
    return [dict(row) for row in rows]


@router.get("/{name}", response_model=AgentResponse)
async def get_agent(name: str):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, version, description, container_image, created_at, updated_at FROM agents WHERE name = $1",
        name,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    return dict(row)


@router.post("/register", response_model=AgentResponse, status_code=201)
async def register_agent(agent: AgentRegister, auth: CurrentAuth):
    pool = await get_pool()
    try:
        row = await pool.fetchrow(
            "INSERT INTO agents (name, version, description, container_image) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, name, version, description, container_image, "
            "created_at, updated_at",
            agent.name,
            agent.version,
            agent.description,
            agent.container_image,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Agent '{agent.name}' already registered",
            ) from e
        raise
    await log_audit(pool, auth, "agent.registered", "agent", agent.name)
    return dict(row)
