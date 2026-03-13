"""Authentication management API endpoints."""

import json

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.auth import (
    AuthContext, get_auth_context, require_scope,
    generate_api_key, hash_api_key, log_audit,
)
from app.database import get_pool

router = APIRouter(tags=["auth"])


# --- Team management ---

class TeamCreate(BaseModel):
    name: str
    description: str | None = None


@router.post("/teams", status_code=201)
async def create_team(team: TeamCreate, auth: AuthContext = Depends(require_scope("admin"))):
    pool = await get_pool()
    try:
        row = await pool.fetchrow(
            "INSERT INTO teams (name, description) VALUES ($1, $2) RETURNING *",
            team.name, team.description,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Team '{team.name}' already exists")
        raise
    await log_audit(pool, auth, "team.created", "team", str(row["id"]))
    return dict(row)


@router.get("/teams")
async def list_teams(auth: AuthContext = Depends(require_scope("read"))):
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM teams ORDER BY name")
    return {"teams": [dict(r) for r in rows]}


# --- API Key management ---

class ApiKeyCreate(BaseModel):
    name: str
    team_id: int | None = None
    scopes: list[str] = ["read", "write"]


@router.post("/api-keys", status_code=201)
async def create_api_key(key_req: ApiKeyCreate, auth: AuthContext = Depends(require_scope("admin"))):
    pool = await get_pool()

    if key_req.team_id:
        team = await pool.fetchrow("SELECT id FROM teams WHERE id = $1", key_req.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    valid_scopes = {"read", "write", "admin"}
    for s in key_req.scopes:
        if s not in valid_scopes:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {s}. Must be one of: {valid_scopes}")

    full_key, prefix = generate_api_key()
    key_hash = hash_api_key(full_key)

    row = await pool.fetchrow(
        "INSERT INTO api_keys (key_hash, key_prefix, name, team_id, scopes) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id, key_prefix, name, team_id, scopes, created_at",
        key_hash, prefix, key_req.name, key_req.team_id, key_req.scopes,
    )

    await log_audit(pool, auth, "api_key.created", "api_key", str(row["id"]))

    result = dict(row)
    result["key"] = full_key  # Only returned on creation
    return result


@router.get("/api-keys")
async def list_api_keys(auth: AuthContext = Depends(require_scope("admin"))):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, key_prefix, name, team_id, scopes, created_at, "
        "expires_at, last_used_at, enabled FROM api_keys ORDER BY created_at"
    )
    return {"api_keys": [dict(r) for r in rows]}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, auth: AuthContext = Depends(require_scope("admin"))):
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE api_keys SET enabled = FALSE WHERE id = $1", key_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="API key not found")
    await log_audit(pool, auth, "api_key.revoked", "api_key", str(key_id))
    return {"revoked": True}


# --- Audit log ---

@router.get("/audit-log")
async def list_audit_log(
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    auth: AuthContext = Depends(require_scope("admin")),
):
    pool = await get_pool()
    query = (
        "SELECT a.id, a.action, a.resource, a.resource_id, a.details, "
        "a.ip_address, a.created_at, k.name as key_name, t.name as team_name "
        "FROM audit_log a "
        "LEFT JOIN api_keys k ON a.api_key_id = k.id "
        "LEFT JOIN teams t ON a.team_id = t.id"
    )
    args = []
    idx = 1

    if action:
        query += f" WHERE a.action = ${idx}"
        args.append(action)
        idx += 1

    query += f" ORDER BY a.created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    args.extend([limit, offset])

    rows = await pool.fetch(query, *args)
    return {"audit_log": [dict(r) for r in rows], "limit": limit, "offset": offset}


# --- Auth info ---

@router.get("/auth/me")
async def auth_info(auth: AuthContext = Depends(get_auth_context)):
    return {
        "authenticated": auth.is_authenticated,
        "key_name": auth.key_name,
        "team_id": auth.team_id,
        "scopes": auth.scopes,
    }
