from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_db, init_db
from app.routes import agents, events, ingestion, jobs, knowledge, logs, reviews, usage, websocket


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(jobs.router)
app.include_router(logs.router)
app.include_router(knowledge.router)
app.include_router(reviews.router)
app.include_router(ingestion.router)
app.include_router(events.router)
app.include_router(usage.router)
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
