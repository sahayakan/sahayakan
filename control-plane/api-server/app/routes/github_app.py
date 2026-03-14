"""GitHub App configuration and installation management endpoints."""

import json
import time
import urllib.error
import urllib.request
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth import AuthContext, get_auth_context, log_audit
from app.database import get_pool
from app.models.github_app import (
    DiscoveryResponse,
    GitHubAppCreate,
    GitHubAppResponse,
    GitHubAppUpdate,
    InstallationResponse,
)
from app.services.github_discovery import discover_repositories

CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]

router = APIRouter(prefix="/github-app", tags=["github-app"])


@router.get("", response_model=list[GitHubAppResponse])
async def list_apps():
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, app_id, app_name, webhook_secret, created_at, updated_at FROM github_apps ORDER BY created_at DESC"
    )
    return [dict(row) for row in rows]


@router.post("", response_model=GitHubAppResponse, status_code=201)
async def create_app(app: GitHubAppCreate, auth: CurrentAuth):
    pool = await get_pool()
    try:
        row = await pool.fetchrow(
            "INSERT INTO github_apps (app_id, app_name, private_key_encrypted, webhook_secret) "
            "VALUES ($1, $2, $3, $4) "
            "RETURNING id, app_id, app_name, webhook_secret, created_at, updated_at",
            app.app_id,
            app.app_name,
            app.private_key,
            app.webhook_secret,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"GitHub App {app.app_id} already exists") from e
        raise
    await log_audit(pool, auth, "github_app.created", "github_app", str(row["id"]))
    return dict(row)


@router.get("/{app_db_id}", response_model=GitHubAppResponse)
async def get_app(app_db_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, app_id, app_name, webhook_secret, created_at, updated_at FROM github_apps WHERE id = $1",
        app_db_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="GitHub App not found")
    return dict(row)


@router.put("/{app_db_id}", response_model=GitHubAppResponse)
async def update_app(app_db_id: int, app: GitHubAppUpdate):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT id FROM github_apps WHERE id = $1", app_db_id)
    if not existing:
        raise HTTPException(status_code=404, detail="GitHub App not found")

    updates = {}
    if app.app_name is not None:
        updates["app_name"] = app.app_name
    if app.private_key is not None:
        updates["private_key_encrypted"] = app.private_key
    if app.webhook_secret is not None:
        updates["webhook_secret"] = app.webhook_secret

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = [f"{k} = ${i + 1}" for i, k in enumerate(updates)]
    set_clauses.append("updated_at = NOW()")
    values = list(updates.values())
    values.append(app_db_id)

    row = await pool.fetchrow(
        f"UPDATE github_apps SET {', '.join(set_clauses)} "
        f"WHERE id = ${len(values)} "
        "RETURNING id, app_id, app_name, webhook_secret, created_at, updated_at",
        *values,
    )
    return dict(row)


@router.delete("/{app_db_id}", status_code=204)
async def delete_app(app_db_id: int, auth: CurrentAuth):
    pool = await get_pool()
    result = await pool.execute("DELETE FROM github_apps WHERE id = $1", app_db_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="GitHub App not found")
    await log_audit(pool, auth, "github_app.deleted", "github_app", str(app_db_id))


@router.get("/{app_db_id}/installations", response_model=list[InstallationResponse])
async def list_installations(app_db_id: int):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, github_app_id, installation_id, account_login, account_type, "
        "is_active, created_at, updated_at "
        "FROM github_app_installations WHERE github_app_id = $1 ORDER BY created_at DESC",
        app_db_id,
    )
    return [dict(row) for row in rows]


@router.delete("/{app_db_id}/installations/{inst_id}", status_code=204)
async def remove_installation(app_db_id: int, inst_id: int):
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM github_app_installations WHERE id = $1 AND github_app_id = $2",
        inst_id,
        app_db_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Installation not found")


@router.post("/{app_db_id}/installations/{inst_id}/discover", response_model=DiscoveryResponse)
async def discover_installation_repos(app_db_id: int, inst_id: int):
    """Discover repositories accessible to a GitHub App installation and register them."""
    pool = await get_pool()
    app_row = await pool.fetchrow(
        "SELECT id, app_id, private_key_encrypted FROM github_apps WHERE id = $1",
        app_db_id,
    )
    if not app_row:
        raise HTTPException(status_code=404, detail="GitHub App not found")

    inst_row = await pool.fetchrow(
        "SELECT id, installation_id FROM github_app_installations WHERE id = $1 AND github_app_id = $2",
        inst_id,
        app_db_id,
    )
    if not inst_row:
        raise HTTPException(status_code=404, detail="Installation not found")

    try:
        repos = await discover_repositories(pool, dict(app_row), dict(inst_row))
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise HTTPException(status_code=400, detail=f"GitHub API error ({e.code}): {body}") from e

    return {"discovered": repos, "count": len(repos)}


@router.post("/{app_db_id}/test")
async def test_app_credentials(app_db_id: int):
    """Test GitHub App credentials by generating a JWT and calling the GitHub API."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT app_id, private_key_encrypted FROM github_apps WHERE id = $1",
        app_db_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="GitHub App not found")

    try:
        import jwt

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": str(row["app_id"]),
        }
        token = jwt.encode(payload, row["private_key_encrypted"], algorithm="RS256")

        req = urllib.request.Request("https://api.github.com/app")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "sahayakan-ingestion")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        return {
            "status": "success",
            "app_name": data.get("name"),
            "app_slug": data.get("slug"),
            "permissions": data.get("permissions", {}),
        }
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=400, detail=f"JWT generation failed: {e}") from e
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise HTTPException(
            status_code=400,
            detail=f"GitHub API error ({e.code}): {body}",
        ) from e
