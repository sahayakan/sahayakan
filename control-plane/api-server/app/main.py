from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import AUTH_ENABLED, PUBLIC_ROUTES, hash_api_key
from app.database import close_db, init_db
from app.routes import (
    agents,
    auth,
    events,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Sahayakan",
    description="Agentic AI platform for software development teams",
    version="0.1.0",
    lifespan=lifespan,
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key auth on all non-public routes when AUTH_ENABLED=true."""

    async def dispatch(self, request, call_next):
        if not AUTH_ENABLED:
            return await call_next(request)

        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        # Allow WebSocket upgrade without middleware interception
        if request.url.path.startswith("/ws"):
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
app.include_router(webhooks.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    from app.database import pool

    db_ok = pool is not None and not pool._closed if pool else False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    from app.metrics import metrics_collector

    return await metrics_collector.collect()
