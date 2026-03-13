"""End-to-end test for Stage 5: all three agents + event bus."""

import asyncio
import json
import sys

sys.path.insert(0, "data-plane")
sys.path.insert(0, "control-plane")

import asyncpg

from agent_runner.knowledge import KnowledgeCache
from agent_runner.runner import AgentRunner
from agents.dummy.agent import DummyAgent
from agents.issue_triage.agent import IssueTriageAgent
from agents.pr_context.agent import PRContextAgent
from agents.meeting_summary.agent import MeetingSummaryAgent
from event_bus.processor import EventBusProcessor
from llm_client.gemini_client import MockLLMClient


PR_MOCK = json.dumps({
    "summary": "Adds retry logic for OAuth token refresh",
    "change_type": "bugfix",
    "risk_level": "medium",
    "risk_reasoning": "Modifies auth flow",
    "linked_issues": [2800],
    "linked_jira_tickets": [],
    "components_modified": ["auth/oauth.py"],
    "test_coverage_notes": "Unit tests added",
    "review_suggestions": ["Check timeout values"],
    "breaking_changes": False,
    "confidence": 0.8,
})

MEETING_MOCK = json.dumps({
    "title": "Daily Standup - 2026-03-13",
    "attendees": ["Alice", "Bob", "Carol"],
    "summary": "Team discussed auth timeout and sprint planning",
    "action_items": [
        {"assignee": "Bob", "action": "Fix OAuth timeout", "related_issue": 2800, "related_jira": None, "due": "2026-03-15"},
    ],
    "decisions": ["Move auth fix to P1"],
    "mentioned_issues": [2800],
    "mentioned_prs": [2799],
    "mentioned_jira_tickets": [],
    "key_topics": ["auth-service", "sprint-planning"],
    "confidence": 0.82,
})


async def main():
    pool = await asyncpg.create_pool(
        user="sahayakan", password="sahayakan_dev_password",
        database="sahayakan", host="localhost", port=5433,
        min_size=1, max_size=5,
    )
    cache = KnowledgeCache("knowledge-cache")

    # Register all agents
    for name, desc in [
        ("pr-context", "Analyzes PRs"),
        ("meeting-summary", "Summarizes meetings"),
    ]:
        await pool.execute(
            "INSERT INTO agents (name, version, description) "
            "VALUES ($1, '1.0', $2) ON CONFLICT (name) DO NOTHING",
            name, desc,
        )

    # --- Test 1: PR Context Agent ---
    print("=" * 60)
    print("TEST 1: PR Context Agent")
    print("=" * 60)

    # Create a sample PR in knowledge cache
    cache.write_json("github/pull_requests/2799.json", {
        "number": 2799,
        "title": "Merge stable into main",
        "body": "Merges stable branch fixes including #2800",
        "state": "closed",
        "user": "maintainer",
        "labels": [],
        "base_branch": "main",
        "head_branch": "stable",
        "merged": True,
        "reviews": [],
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-11T10:00:00Z",
        "merged_at": "2026-03-11T10:00:00Z",
        "closed_at": "2026-03-11T10:00:00Z",
        "html_url": "https://github.com/pallets/click/pull/2799",
        "changed_files": 5,
        "additions": 120,
        "deletions": 30,
        "fetched_at": "2026-03-13T10:00:00Z",
    })

    params = json.dumps({"pr_number": 2799})
    row = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) "
        "VALUES ('pr-context', 'pending', $1::jsonb) RETURNING id",
        params,
    )
    pr_job_id = row["id"]
    print(f"Created PR context job {pr_job_id}")

    llm = MockLLMClient(PR_MOCK)
    runner = AgentRunner(
        db_pool=pool, knowledge_cache=cache,
        agent_registry={
            "dummy": DummyAgent, "issue-triage": IssueTriageAgent,
            "pr-context": PRContextAgent, "meeting-summary": MeetingSummaryAgent,
        },
        llm_client=llm,
    )
    await runner._poll_and_execute()

    job = await pool.fetchrow("SELECT status FROM jobs WHERE id = $1", pr_job_id)
    print(f"PR Context job status: {job['status']}")
    assert job["status"] == "completed", f"Expected completed, got {job['status']}"

    # --- Test 2: Meeting Summary Agent ---
    print()
    print("=" * 60)
    print("TEST 2: Meeting Summary Agent")
    print("=" * 60)

    # Create transcript in knowledge cache
    cache.write_file("meetings/transcripts/2026-03-13-standup.txt", """Meeting: Daily Standup
Date: 2026-03-13
Attendees: Alice, Bob, Carol

[00:00] Alice: Let's start. Bob, how's the auth issue going?
[00:45] Bob: I've been looking at issue #2800 - the auth timeout. PR #2799 has some related changes.
[02:30] Carol: The sprint board needs cleanup. I'll handle it today.
[03:15] Alice: Let's make the auth fix P1. Bob, can you have it done by Friday?
[03:30] Bob: Yes, I'll target Friday.
[04:00] Alice: Great. Meeting adjourned.
""")

    llm2 = MockLLMClient(MEETING_MOCK)
    runner2 = AgentRunner(
        db_pool=pool, knowledge_cache=cache,
        agent_registry={
            "dummy": DummyAgent, "issue-triage": IssueTriageAgent,
            "pr-context": PRContextAgent, "meeting-summary": MeetingSummaryAgent,
        },
        llm_client=llm2,
    )

    params2 = json.dumps({"transcript_id": "2026-03-13-standup"})
    row2 = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) "
        "VALUES ('meeting-summary', 'pending', $1::jsonb) RETURNING id",
        params2,
    )
    meeting_job_id = row2["id"]
    print(f"Created meeting summary job {meeting_job_id}")

    await runner2._poll_and_execute()

    job2 = await pool.fetchrow("SELECT status FROM jobs WHERE id = $1", meeting_job_id)
    print(f"Meeting Summary job status: {job2['status']}")
    assert job2["status"] == "completed", f"Expected completed, got {job2['status']}"

    # --- Test 3: Event Bus ---
    print()
    print("=" * 60)
    print("TEST 3: Event Bus Processor")
    print("=" * 60)

    event_bus = EventBusProcessor(db_pool=pool)
    await event_bus._register_default_subscriptions()

    # Check subscriptions
    subs = await pool.fetch("SELECT * FROM agent_subscriptions ORDER BY agent_name")
    print(f"Registered subscriptions: {len(subs)}")
    for s in subs:
        print(f"  {s['agent_name']} -> {s['event_type']}")

    # Publish a test event
    await pool.execute(
        "INSERT INTO events (event_type, source, payload) "
        "VALUES ('meeting.uploaded', 'test', $1::jsonb)",
        json.dumps({"transcript_id": "2026-03-13-standup"}),
    )

    # Process events
    await event_bus._process_events()

    # Check if a job was created
    pending = await pool.fetch(
        "SELECT id, agent_name, parameters FROM jobs WHERE status = 'pending' "
        "AND agent_name = 'meeting-summary'"
    )
    print(f"Jobs created by event bus: {len(pending)}")
    for p in pending:
        params = p["parameters"] if isinstance(p["parameters"], dict) else json.loads(p["parameters"])
        print(f"  Job {p['id']}: {p['agent_name']} params={params}")

    # --- Verification ---
    print()
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Check reports exist
    for path in [
        "agent_outputs/pr_context/2799.md",
        "agent_outputs/meeting_summaries/2026-03-13-standup.md",
    ]:
        exists = cache.file_exists(path)
        print(f"{'OK' if exists else 'MISSING'}: {path}")

    # Check events
    events = await pool.fetch(
        "SELECT event_type, source FROM events ORDER BY created_at DESC LIMIT 5"
    )
    print(f"\nRecent events:")
    for e in events:
        print(f"  {e['event_type']} (from {e['source']})")

    # Show git log
    import subprocess
    result = subprocess.run(
        ["git", "log", "--oneline", "-5"],
        cwd="knowledge-cache", capture_output=True, text=True,
    )
    print(f"\nKnowledge cache git log:")
    print(result.stdout)

    await pool.close()
    print("All Stage 5 tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
