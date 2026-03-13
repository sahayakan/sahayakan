"""End-to-end test for Stage 7: Semantic Memory."""

import asyncio
import json
import sys

sys.path.insert(0, "data-plane")

import asyncpg

from agent_runner.embedding_service import (
    EmbeddingService,
    MockEmbeddingProvider,
)
from agent_runner.knowledge import KnowledgeCache


def _meta(r):
    m = r.get("metadata")
    if isinstance(m, str):
        import json as _json

        return _json.loads(m)
    return m or {}


async def main():
    pool = await asyncpg.create_pool(
        user="sahayakan",
        password="sahayakan_dev_password",
        database="sahayakan",
        host="localhost",
        port=5433,
        min_size=1,
        max_size=3,
    )
    cache = KnowledgeCache("knowledge-cache")
    provider = MockEmbeddingProvider()
    service = EmbeddingService(db_pool=pool, provider=provider)

    # Test 1: Backfill from knowledge cache
    print("=" * 60)
    print("TEST 1: Backfill embeddings from knowledge cache")
    print("=" * 60)
    counts = await service.backfill_from_cache(cache)
    print(f"Embedded: {counts}")

    total = await service.get_embedding_count()
    print(f"Total embeddings by type: {total}")

    # Test 2: Semantic search
    print()
    print("=" * 60)
    print("TEST 2: Semantic search")
    print("=" * 60)

    results = await service.search("authentication timeout", limit=5)
    print(f"Search 'authentication timeout': {len(results)} results")
    for r in results:
        print(f"  {r['similarity']:.3f} {r['source_type']}/{r['source_id']} - {_meta(r).get('title', '')[:50]}")

    # Test 3: Filtered search
    print()
    results = await service.search("context cleanup", source_types=["issue"], limit=5)
    print(f"Search 'context cleanup' (issues only): {len(results)} results")
    for r in results:
        print(f"  {r['similarity']:.3f} {r['source_type']}/{r['source_id']}")

    # Test 4: Embed and search for new content
    print()
    print("=" * 60)
    print("TEST 3: Embed new content and search")
    print("=" * 60)
    await service.embed_and_store(
        "issue",
        "9999",
        "Login page crashes when OAuth token expires during session refresh",
        metadata={"title": "Login crash on token expiry", "state": "open"},
    )

    results = await service.search("OAuth token crash", source_types=["issue"], limit=3)
    print(f"Search after adding new issue: {len(results)} results")
    for r in results:
        print(f"  {r['similarity']:.3f} {r['source_type']}/{r['source_id']} - {_meta(r).get('title', '')[:50]}")

    # Test 5: Duplicate detection won't re-embed
    print()
    print("=" * 60)
    print("TEST 4: Idempotent embedding")
    print("=" * 60)
    updated = await service.embed_and_store(
        "issue",
        "9999",
        "Login page crashes when OAuth token expires during session refresh",
        metadata={"title": "Login crash on token expiry"},
    )
    print(f"Re-embed same content: updated={updated} (expected False)")
    assert not updated, "Should not re-embed identical content"

    # Test 6: Verify via API
    print()
    print("=" * 60)
    print("TEST 5: API endpoints")
    print("=" * 60)
    import urllib.request

    # Stats
    resp = urllib.request.urlopen("http://localhost:8000/knowledge/search/stats")
    stats = json.loads(resp.read())
    print(f"Stats: {stats}")

    # Search via API (may return 501 if embedding service not in container)
    try:
        req = urllib.request.Request(
            "http://localhost:8000/knowledge/search",
            data=json.dumps({"query": "auth timeout", "limit": 3}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        search_result = json.loads(resp.read())
        print(f"API search results: {len(search_result['results'])}")
        print(f"Total indexed: {search_result['total_embeddings']}")
    except urllib.error.HTTPError as e:
        if e.code == 501:
            print("API search: 501 (embedding service not in container - expected)")
        else:
            raise

    await pool.close()
    print()
    print("All Stage 7 tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
