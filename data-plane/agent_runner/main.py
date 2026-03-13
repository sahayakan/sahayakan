"""Entry point for the agent runner service."""

import asyncio
import os
import sys

# Add data-plane directory to Python path for imports
DATA_PLANE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DATA_PLANE_DIR not in sys.path:
    sys.path.insert(0, DATA_PLANE_DIR)

import asyncpg

from agent_runner.knowledge import KnowledgeCache
from agent_runner.runner import AgentRunner
from agents.dummy.agent import DummyAgent


def get_agent_registry() -> dict:
    """Return mapping of agent names to their classes."""
    return {
        "dummy": DummyAgent,
    }


async def main():
    db_pool = await asyncpg.create_pool(
        user=os.environ.get("POSTGRES_USER", "sahayakan"),
        password=os.environ.get("POSTGRES_PASSWORD", "sahayakan_dev_password"),
        database=os.environ.get("POSTGRES_DB", "sahayakan"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        min_size=2,
        max_size=5,
    )

    cache_path = os.environ.get(
        "KNOWLEDGE_CACHE_PATH",
        os.path.join(os.path.dirname(DATA_PLANE_DIR), "knowledge-cache"),
    )
    knowledge_cache = KnowledgeCache(cache_path)

    runner = AgentRunner(
        db_pool=db_pool,
        knowledge_cache=knowledge_cache,
        agent_registry=get_agent_registry(),
    )

    try:
        await runner.start()
    except KeyboardInterrupt:
        await runner.stop()
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
