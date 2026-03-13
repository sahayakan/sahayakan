"""Semantic context collection for agents using embedding search."""

from agent_runner.embedding_service import EmbeddingService


async def find_similar_issues(
    embedding_service: EmbeddingService,
    query_text: str,
    exclude_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Find issues semantically similar to the query text."""
    results = await embedding_service.search(query_text, source_types=["issue"], limit=limit + 1)
    return [r for r in results if r["source_id"] != exclude_id and r["similarity"] > 0.3][:limit]


async def find_related_prs(
    embedding_service: EmbeddingService,
    query_text: str,
    limit: int = 5,
) -> list[dict]:
    """Find PRs semantically related to the query text."""
    results = await embedding_service.search(query_text, source_types=["pr"], limit=limit)
    return [r for r in results if r["similarity"] > 0.3]


async def find_related_jira(
    embedding_service: EmbeddingService,
    query_text: str,
    limit: int = 5,
) -> list[dict]:
    """Find Jira tickets semantically related to the query text."""
    results = await embedding_service.search(query_text, source_types=["jira"], limit=limit)
    return [r for r in results if r["similarity"] > 0.3]


async def find_related_reports(
    embedding_service: EmbeddingService,
    query_text: str,
    limit: int = 5,
) -> list[dict]:
    """Find previous agent reports semantically related to the query text."""
    results = await embedding_service.search(query_text, source_types=["report"], limit=limit)
    return [r for r in results if r["similarity"] > 0.3]
