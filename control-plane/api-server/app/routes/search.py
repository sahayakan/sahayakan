"""Semantic search API endpoint."""

import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str
    types: list[str] | None = None
    limit: int = 10


@router.post("/search")
async def semantic_search(request: SearchRequest):
    pool = await get_pool()

    # Check if embeddings table exists and has data
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM embeddings")
    except Exception:
        raise HTTPException(
            status_code=501,
            detail="Embeddings table not available. Run migration 002_pgvector_embeddings.sql",
        )

    if count == 0:
        return {
            "results": [],
            "total_embeddings": 0,
            "message": "No embeddings yet. Run backfill to index existing content.",
        }

    # Use the embedding service
    try:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root / "data-plane"))
        from agent_runner.embedding_service import (
            EmbeddingService,
            MockEmbeddingProvider,
            VertexAIEmbeddingProvider,
        )

        vertex_project = os.environ.get("VERTEX_PROJECT")
        if vertex_project:
            provider = VertexAIEmbeddingProvider(
                project=vertex_project,
                location=os.environ.get("VERTEX_LOCATION", "us-central1"),
            )
        else:
            provider = MockEmbeddingProvider()

        service = EmbeddingService(db_pool=pool, provider=provider)
        results = await service.search(
            query=request.query,
            source_types=request.types,
            limit=request.limit,
        )

        return {
            "query": request.query,
            "results": results,
            "total_embeddings": count,
        }

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Embedding service not available in this deployment",
        )


@router.get("/search/stats")
async def embedding_stats():
    pool = await get_pool()
    try:
        rows = await pool.fetch(
            "SELECT source_type, COUNT(*) as count "
            "FROM embeddings GROUP BY source_type ORDER BY source_type"
        )
        total = sum(r["count"] for r in rows)
        return {
            "total_embeddings": total,
            "by_type": {r["source_type"]: r["count"] for r in rows},
        }
    except Exception:
        return {"total_embeddings": 0, "by_type": {}, "message": "Embeddings table not available"}
