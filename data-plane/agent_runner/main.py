"""Entry point for the agent runner service."""

import asyncio
import os
import sys

# Add data-plane directory to Python path for imports
DATA_PLANE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DATA_PLANE_DIR not in sys.path:
    sys.path.insert(0, DATA_PLANE_DIR)

import asyncpg  # noqa: E402

from agent_runner.knowledge import KnowledgeCache  # noqa: E402
from agent_runner.runner import AgentRunner  # noqa: E402
from agents.dummy.agent import DummyAgent  # noqa: E402
from agents.insights.agent import InsightsAgent  # noqa: E402
from agents.issue_triage.agent import IssueTriageAgent  # noqa: E402
from agents.meeting_summary.agent import MeetingSummaryAgent  # noqa: E402
from agents.pr_context.agent import PRContextAgent  # noqa: E402
from agents.slack_digest.agent import SlackDigestAgent  # noqa: E402
from agents.trend_analysis.agent import TrendAnalysisAgent  # noqa: E402


def get_llm_client():
    """Create the appropriate LLM client based on environment."""
    vertex_project = os.environ.get("VERTEX_PROJECT")
    if vertex_project:
        from llm_client.gemini_client import GeminiClient

        return GeminiClient(
            project=vertex_project,
            location=os.environ.get("VERTEX_LOCATION", "us-central1"),
        )
    else:
        # Use mock client for development/testing
        from llm_client.gemini_client import MockLLMClient

        print("[Runner] No VERTEX_PROJECT set, using MockLLMClient", flush=True)
        return MockLLMClient()


def get_agent_registry() -> dict:
    """Return mapping of agent names to their classes."""
    return {
        "dummy": DummyAgent,
        "issue-triage": IssueTriageAgent,
        "pr-context": PRContextAgent,
        "meeting-summary": MeetingSummaryAgent,
        "slack-digest": SlackDigestAgent,
        "insights": InsightsAgent,
        "trend-analysis": TrendAnalysisAgent,
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
    llm_client = get_llm_client()

    runner = AgentRunner(
        db_pool=db_pool,
        knowledge_cache=knowledge_cache,
        agent_registry=get_agent_registry(),
        llm_client=llm_client,
    )

    # Handle SIGTERM for graceful shutdown
    import signal

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(runner.stop()))

    try:
        await runner.start()
    except KeyboardInterrupt:
        await runner.stop()
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
