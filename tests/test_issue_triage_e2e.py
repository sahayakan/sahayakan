"""End-to-end test for the Issue Triage Agent pipeline."""

import asyncio
import json
import os
import sys

sys.path.insert(0, "data-plane")

import asyncpg

from agent_runner.knowledge import KnowledgeCache
from agent_runner.runner import AgentRunner
from agents.dummy.agent import DummyAgent
from agents.issue_triage.agent import IssueTriageAgent
from llm_client.gemini_client import MockLLMClient

MOCK_RESPONSE = json.dumps(
    {
        "summary": "Shell completion context cleanup issue",
        "priority": "medium",
        "priority_reasoning": "Code cleanup for shell completion, not a user-facing bug",
        "is_duplicate": False,
        "possible_duplicates": [],
        "related_prs": [2799],
        "related_jira_tickets": [],
        "affected_components": ["shell-completion", "context-management"],
        "suggested_labels": ["cleanup", "shell-completion"],
        "suggested_actions": [
            "Review the context lifecycle in shell completion",
            "Check if related PR #2799 addresses the same concern",
        ],
        "confidence": 0.75,
    }
)


async def main():
    pool = await asyncpg.create_pool(
        user=os.environ.get("POSTGRES_USER", "sahayakan"),
        password=os.environ.get("POSTGRES_PASSWORD", "sahayakan_dev_password"),
        database=os.environ.get("POSTGRES_DB", "sahayakan"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        min_size=1,
        max_size=3,
    )

    # Register issue-triage agent if not already
    await pool.execute(
        "INSERT INTO agents (name, version, description) "
        "VALUES ('issue-triage', '1.0', 'Analyzes GitHub issues') "
        "ON CONFLICT (name) DO NOTHING"
    )

    # Create a job for issue #2800
    params = json.dumps({"issue_id": 2800})
    row = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) VALUES ('issue-triage', 'pending', $1::jsonb) RETURNING id",
        params,
    )
    job_id = row["id"]
    print(f"Created job {job_id}")

    cache = KnowledgeCache("knowledge-cache")
    llm = MockLLMClient(MOCK_RESPONSE)

    runner = AgentRunner(
        db_pool=pool,
        knowledge_cache=cache,
        agent_registry={
            "dummy": DummyAgent,
            "issue-triage": IssueTriageAgent,
        },
        llm_client=llm,
    )

    await runner._poll_and_execute()

    # Verify results
    job = await pool.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    print(f"\nJob status: {job['status']}")

    run_row = await pool.fetchrow("SELECT * FROM agent_runs WHERE job_id = $1", job_id)
    print(f"Run status: {run_row['status']}")
    print(f"Git commit: {run_row['git_commit'][:8] if run_row['git_commit'] else 'None'}")

    artifacts = await pool.fetch("SELECT * FROM artifacts WHERE run_id = $1", run_row["id"])
    print(f"Artifacts: {len(artifacts)}")
    for a in artifacts:
        print(f"  - {a['storage_uri']}")

    llm_row = await pool.fetchrow("SELECT * FROM llm_usage WHERE run_id = $1", run_row["id"])
    if llm_row:
        print(
            f"LLM usage: model={llm_row['model']}, "
            f"tokens_in={llm_row['tokens_input']}, "
            f"tokens_out={llm_row['tokens_output']}"
        )

    event = await pool.fetchrow(
        "SELECT * FROM events WHERE event_type = 'issue.analyzed' ORDER BY created_at DESC LIMIT 1"
    )
    if event:
        print(f"Event: {event['event_type']}")
        payload = json.loads(event["payload"]) if isinstance(event["payload"], str) else event["payload"]
        print(f"  priority: {payload.get('priority')}")
        print(f"  confidence: {payload.get('confidence')}")

    # Show the generated report
    report_path = "knowledge-cache/agent_outputs/issue_analysis/2800.md"
    try:
        with open(report_path) as f:
            print("\n--- Generated Report ---")
            print(f.read())
    except FileNotFoundError:
        print(f"Report not found at {report_path}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
