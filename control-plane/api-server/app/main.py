import asyncio
import contextlib
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import AUTH_ENABLED, PUBLIC_ROUTES, hash_api_key
from app.database import close_db, init_db
from app.log_store import cleanup_stale_jobs, init_log_persistence
from app.request_context import set_request_id
from app.routes import (
    agents,
    auth,
    events,
    github_app,
    ingestion,
    insights,
    jira_projects,
    jobs,
    knowledge,
    logs,
    repositories,
    reviews,
    schedules,
    search,
    usage,
    webhooks,
    websocket,
)


async def _cleanup_loop():
    """Hourly in-memory log cleanup + daily DB log cleanup."""
    from app.database import pool

    hour_count = 0
    while True:
        await asyncio.sleep(3600)
        cleanup_stale_jobs(max_age_hours=24)
        hour_count += 1
        if hour_count >= 24:
            hour_count = 0
            if pool:
                with contextlib.suppress(Exception):
                    await pool.execute("DELETE FROM job_logs WHERE created_at < NOW() - INTERVAL '30 days'")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.database import pool

    init_log_persistence(pool)
    cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    cleanup_task.cancel()
    await close_db()


app = FastAPI(
    title="Sahayakan",
    description="Agentic AI platform for software development teams",
    version="0.1.0",
    lifespan=lifespan,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into request state, context var, and response headers."""

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key auth on all non-public routes when AUTH_ENABLED=true."""

    async def dispatch(self, request, call_next):
        if not AUTH_ENABLED:
            return await call_next(request)

        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        # Allow WebSocket and webhook paths through (they handle their own auth)
        if request.url.path.startswith("/ws") or request.url.path.startswith("/webhooks"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        # Allow requests with basic auth through (already authenticated by reverse proxy)
        if auth_header.startswith("Basic "):
            return await call_next(request)
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "API key required"})

        token = auth_header[7:]
        key_hash = hash_api_key(token)

        from app.database import pool

        if not pool:
            return await call_next(request)

        row = await pool.fetchrow("SELECT id, enabled FROM api_keys WHERE key_hash = $1", key_hash)
        if not row or not row["enabled"]:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        return await call_next(request)


app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(jobs.router)
app.include_router(logs.router)
app.include_router(knowledge.router)
app.include_router(reviews.router)
app.include_router(ingestion.router)
app.include_router(events.router)
app.include_router(insights.router)
app.include_router(schedules.router)
app.include_router(search.router)
app.include_router(usage.router)
app.include_router(repositories.router)
app.include_router(jira_projects.router)
app.include_router(github_app.router)
app.include_router(webhooks.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    import os
    import urllib.request

    from app.database import pool

    start_ms = time.time() * 1000

    # DB check: actually query
    db_ok = False
    if pool and not pool._closed:
        try:
            await pool.fetchval("SELECT 1")
            db_ok = True
        except Exception:
            pass

    # MinIO check
    minio_ok = False
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    try:
        urllib.request.urlopen(f"http://{minio_endpoint}/minio/health/live", timeout=2)
        minio_ok = True
    except Exception:
        pass

    # Event bus status
    event_bus = {}
    if pool and db_ok:
        try:
            unprocessed = await pool.fetchval("SELECT COUNT(*) FROM events WHERE processed = FALSE")
            last_event = await pool.fetchval("SELECT MAX(created_at) FROM events WHERE processed = TRUE")
            event_bus = {
                "unprocessed": unprocessed,
                "last_processed": str(last_event) if last_event else None,
            }
        except Exception:
            pass

    # Last successful job
    last_job = None
    if pool and db_ok:
        try:
            row = await pool.fetchrow(
                "SELECT id, agent_name, completed_at FROM jobs "
                "WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1"
            )
            if row:
                last_job = {
                    "id": row["id"],
                    "agent": row["agent_name"],
                    "completed_at": str(row["completed_at"]),
                }
        except Exception:
            pass

    uptime_ms = round(time.time() * 1000 - start_ms, 1)
    all_ok = db_ok and minio_ok
    return {
        "status": "healthy" if all_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "minio": "connected" if minio_ok else "disconnected",
        "event_bus": event_bus,
        "last_job": last_job,
        "uptime_check_ms": uptime_ms,
        "version": "0.1.0",
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    from app.metrics import metrics_collector

    return await metrics_collector.collect()
