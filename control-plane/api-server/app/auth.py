"""Authentication and authorization middleware.

API key authentication with RBAC scopes.
Keys are passed via Authorization: Bearer <key> header.
"""

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_pool

security = HTTPBearer(auto_error=False)

# Routes that don't require authentication
PUBLIC_ROUTES = {"/health", "/docs", "/openapi.json", "/redoc"}

# Auth can be disabled via environment variable for development
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"


@dataclass
class AuthContext:
    """Authenticated request context."""

    api_key_id: int | None = None
    team_id: int | None = None
    scopes: list[str] | None = None
    key_name: str = ""

    @property
    def is_authenticated(self) -> bool:
        return self.api_key_id is not None

    def has_scope(self, scope: str) -> bool:
        if not self.scopes:
            return True  # No scopes = all access (dev mode)
        return scope in self.scopes or "admin" in self.scopes


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (full_key, prefix)."""
    key = f"sk_{secrets.token_urlsafe(32)}"
    prefix = key[:10]
    return key, prefix


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> AuthContext:
    """Extract and validate authentication from request."""
    # Skip auth for public routes
    if request.url.path in PUBLIC_ROUTES:
        return AuthContext()

    # Skip auth if disabled
    if not AUTH_ENABLED:
        return AuthContext(scopes=["admin"])

    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    key = credentials.credentials
    key_hash = hash_api_key(key)

    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, team_id, scopes, name, enabled, expires_at FROM api_keys WHERE key_hash = $1",
        key_hash,
    )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not row["enabled"]:
        raise HTTPException(status_code=403, detail="API key is disabled")

    if row["expires_at"] and row["expires_at"] < datetime.now(UTC).replace(tzinfo=None):
        raise HTTPException(status_code=403, detail="API key has expired")

    # Update last_used_at
    await pool.execute(
        "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1",
        row["id"],
    )

    return AuthContext(
        api_key_id=row["id"],
        team_id=row["team_id"],
        scopes=row["scopes"],
        key_name=row["name"],
    )


def require_scope(scope: str):
    """Dependency that checks for a required scope."""

    async def _check(auth: Annotated[AuthContext, Depends(get_auth_context)] = None):
        if not auth.has_scope(scope):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {scope}",
            )
        return auth

    return _check


async def log_audit(
    pool,
    auth: AuthContext,
    action: str,
    resource: str = "",
    resource_id: str = "",
    details: dict | None = None,
    ip_address: str = "",
) -> None:
    """Record an action in the audit log."""
    try:
        import json

        await pool.execute(
            "INSERT INTO audit_log "
            "(api_key_id, team_id, action, resource, resource_id, details, ip_address) "
            "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)",
            auth.api_key_id,
            auth.team_id,
            action,
            resource,
            resource_id,
            json.dumps(details) if details else None,
            ip_address,
        )
    except Exception:
        pass  # Audit logging is best-effort
