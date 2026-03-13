"""Embedding service for semantic search across the knowledge cache.

Generates vector embeddings and stores them in PostgreSQL (pgvector).
Supports both real Vertex AI embeddings and a mock for development.
"""

import hashlib
import json
from abc import ABC, abstractmethod

import asyncpg


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    DIMENSION = 768

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""


class VertexAIEmbeddingProvider(EmbeddingProvider):
    """Real Vertex AI embedding provider."""

    def __init__(self, project: str, location: str = "us-central1"):
        self.project = project
        self.location = location
        self._model = None

    def _get_model(self):
        if self._model is None:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel

            vertexai.init(project=self.project, location=self.location)
            self._model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        # Truncate to model limit
        truncated = text[:8000]
        embeddings = model.get_embeddings([truncated])
        return embeddings[0].values


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock provider that generates deterministic embeddings from text hash.

    Useful for development and testing without Vertex AI credentials.
    Similar texts will produce somewhat similar vectors.
    """

    def embed(self, text: str) -> list[float]:
        # Generate a deterministic pseudo-embedding from text content
        h = hashlib.sha256(text.encode()).hexdigest()
        # Use hash bytes to seed a simple vector
        values = []
        for i in range(0, min(len(h), self.DIMENSION * 2), 2):
            if len(values) >= self.DIMENSION:
                break
            byte_val = int(h[i : i + 2], 16)
            values.append((byte_val - 128) / 128.0)
        # Pad to full dimension
        while len(values) < self.DIMENSION:
            values.append(0.0)
        # Normalize
        magnitude = sum(v * v for v in values) ** 0.5
        if magnitude > 0:
            values = [v / magnitude for v in values]
        return values


class EmbeddingService:
    """High-level service for embedding and searching content."""

    def __init__(self, db_pool: asyncpg.Pool, provider: EmbeddingProvider):
        self.pool = db_pool
        self.provider = provider

    def _content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def embed_and_store(
        self,
        source_type: str,
        source_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> bool:
        """Embed text and store in database. Returns True if updated."""
        content_hash = self._content_hash(text)

        # Check if already embedded with same content
        existing = await self.pool.fetchrow(
            "SELECT content_hash FROM embeddings WHERE source_type = $1 AND source_id = $2",
            source_type,
            source_id,
        )
        if existing and existing["content_hash"] == content_hash:
            return False  # Already up to date

        # Generate embedding
        vector = self.provider.embed(text)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"

        await self.pool.execute(
            "INSERT INTO embeddings "
            "(source_type, source_id, content_hash, embedding, metadata) "
            "VALUES ($1, $2, $3, $4::vector, $5::jsonb) "
            "ON CONFLICT (source_type, source_id) DO UPDATE SET "
            "content_hash = $3, embedding = $4::vector, "
            "metadata = $5::jsonb, created_at = NOW()",
            source_type,
            source_id,
            content_hash,
            vector_str,
            json.dumps(metadata) if metadata else None,
        )
        return True

    async def search(
        self,
        query: str,
        source_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Semantic search across embedded content."""
        query_vector = self.provider.embed(query)
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        if source_types:
            placeholders = ", ".join(f"${i + 2}" for i in range(len(source_types)))
            rows = await self.pool.fetch(
                f"SELECT source_type, source_id, metadata, "
                f"1 - (embedding <=> $1::vector) as similarity "
                f"FROM embeddings "
                f"WHERE source_type IN ({placeholders}) "
                f"ORDER BY embedding <=> $1::vector "
                f"LIMIT ${len(source_types) + 2}",
                vector_str,
                *source_types,
                limit,
            )
        else:
            rows = await self.pool.fetch(
                "SELECT source_type, source_id, metadata, "
                "1 - (embedding <=> $1::vector) as similarity "
                "FROM embeddings "
                "ORDER BY embedding <=> $1::vector "
                "LIMIT $2",
                vector_str,
                limit,
            )

        return [
            {
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "similarity": float(r["similarity"]),
                "metadata": r["metadata"],
            }
            for r in rows
        ]

    async def embed_issue(self, issue_data: dict) -> bool:
        """Embed a GitHub issue."""
        text = (
            f"{issue_data.get('title', '')} "
            f"{issue_data.get('body', '')} "
            f"Labels: {', '.join(issue_data.get('labels', []))}"
        )
        return await self.embed_and_store(
            "issue",
            str(issue_data["number"]),
            text,
            metadata={
                "title": issue_data.get("title", ""),
                "state": issue_data.get("state", ""),
                "labels": issue_data.get("labels", []),
            },
        )

    async def embed_pr(self, pr_data: dict) -> bool:
        """Embed a GitHub pull request."""
        text = f"{pr_data.get('title', '')} {pr_data.get('body', '')} Labels: {', '.join(pr_data.get('labels', []))}"
        return await self.embed_and_store(
            "pr",
            str(pr_data["number"]),
            text,
            metadata={
                "title": pr_data.get("title", ""),
                "state": pr_data.get("state", ""),
                "merged": pr_data.get("merged", False),
            },
        )

    async def embed_jira_ticket(self, ticket_data: dict) -> bool:
        """Embed a Jira ticket."""
        text = (
            f"{ticket_data.get('summary', '')} "
            f"{ticket_data.get('description', '')} "
            f"Status: {ticket_data.get('status', '')} "
            f"Priority: {ticket_data.get('priority', '')}"
        )
        return await self.embed_and_store(
            "jira",
            ticket_data["key"],
            text,
            metadata={
                "summary": ticket_data.get("summary", ""),
                "status": ticket_data.get("status", ""),
                "priority": ticket_data.get("priority", ""),
            },
        )

    async def embed_report(self, report_type: str, report_id: str, report_data: dict) -> bool:
        """Embed an agent report."""
        text = json.dumps(report_data, indent=2)[:6000]
        return await self.embed_and_store(
            "report",
            f"{report_type}/{report_id}",
            text,
            metadata={
                "type": report_type,
                "summary": report_data.get("summary", ""),
            },
        )

    async def get_embedding_count(self) -> dict:
        """Get count of embeddings by source type."""
        rows = await self.pool.fetch("SELECT source_type, COUNT(*) as count FROM embeddings GROUP BY source_type")
        return {r["source_type"]: r["count"] for r in rows}

    async def backfill_from_cache(self, knowledge_cache) -> dict:
        """Backfill embeddings from existing knowledge cache content."""
        counts = {"issues": 0, "prs": 0, "jira": 0, "reports": 0}

        # Embed issues
        for f in knowledge_cache.list_files("github/issues", "*.json"):
            try:
                data = knowledge_cache.read_json(f)
                if await self.embed_issue(data):
                    counts["issues"] += 1
            except Exception:
                pass

        # Embed PRs
        for f in knowledge_cache.list_files("github/pull_requests", "*.json"):
            try:
                data = knowledge_cache.read_json(f)
                if await self.embed_pr(data):
                    counts["prs"] += 1
            except Exception:
                pass

        # Embed Jira tickets
        for f in knowledge_cache.list_files("jira/tickets", "*.json"):
            try:
                data = knowledge_cache.read_json(f)
                if await self.embed_jira_ticket(data):
                    counts["jira"] += 1
            except Exception:
                pass

        # Embed reports
        for report_type in ("issue_analysis", "pr_context", "meeting_summaries"):
            for f in knowledge_cache.list_files(f"agent_outputs/{report_type}", "*.json"):
                try:
                    data = knowledge_cache.read_json(f)
                    rid = f.split("/")[-1].replace(".json", "")
                    if await self.embed_report(report_type, rid, data):
                        counts["reports"] += 1
                except Exception:
                    pass

        return counts
