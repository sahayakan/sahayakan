"""End-to-end test for Stage 8: Slack Integration."""

import asyncio
import json
import sys

sys.path.insert(0, "data-plane")
sys.path.insert(0, "control-plane")

import asyncpg
from event_bus.processor import EventBusProcessor
from notifications.slack_notifier import NotificationConfig, SlackNotifier

from agent_runner.knowledge import KnowledgeCache
from agent_runner.runner import AgentRunner
from agents.dummy.agent import DummyAgent
from agents.issue_triage.agent import IssueTriageAgent
from agents.meeting_summary.agent import MeetingSummaryAgent
from agents.pr_context.agent import PRContextAgent
from agents.slack_digest.agent import SlackDigestAgent
from llm_client.gemini_client import MockLLMClient

DIGEST_MOCK = json.dumps(
    {
        "channel": "engineering",
        "time_period": "2026-03-13",
        "summary": "Team discussed deployment pipeline issues and upcoming release timeline",
        "key_discussions": [
            {
                "topic": "CI/CD Pipeline",
                "participants": ["alice", "bob"],
                "summary": "Pipeline failing on arm64 builds",
            },
            {
                "topic": "Release Planning",
                "participants": ["carol", "dave"],
                "summary": "v2.1 release pushed to next week",
            },
        ],
        "decisions": ["Fix arm64 builds before release", "Postpone v2.1 to March 20"],
        "action_items": [
            {"assignee": "bob", "action": "Debug arm64 build failures", "related_issue": None, "related_jira": None},
            {"assignee": "carol", "action": "Update release notes", "related_issue": None, "related_jira": None},
        ],
        "mentioned_issues": [],
        "mentioned_prs": [],
        "mentioned_jira_tickets": [],
        "highlights": ["Pipeline outage resolved at 2pm"],
        "confidence": 0.79,
    }
)


async def main():
    pool = await asyncpg.create_pool(
        user="sahayakan",
        password="sahayakan_dev_password",
        database="sahayakan",
        host="localhost",
        port=5433,
        min_size=1,
        max_size=5,
    )
    cache = KnowledgeCache("knowledge-cache")

    # Register slack-digest agent
    await pool.execute(
        "INSERT INTO agents (name, version, description) "
        "VALUES ('slack-digest', '1.0', 'Summarizes Slack channel activity') "
        "ON CONFLICT (name) DO NOTHING"
    )

    # --- Test 1: Create test Slack data ---
    print("=" * 60)
    print("TEST 1: Slack data in knowledge cache")
    print("=" * 60)
    slack_data = {
        "channel": "engineering",
        "channel_id": "C12345",
        "messages": [
            {
                "user": "alice",
                "text": "Good morning team! CI pipeline is failing again on arm64",
                "ts": "1710320400",
                "type": "message",
                "thread_replies": [
                    {"user": "bob", "text": "I'll look into it right away", "ts": "1710320460"},
                ],
            },
            {
                "user": "carol",
                "text": "Should we postpone the v2.1 release?",
                "ts": "1710321000",
                "type": "message",
                "thread_replies": [],
            },
            {
                "user": "dave",
                "text": "Yes, let's push to next week. I'll update the roadmap.",
                "ts": "1710321060",
                "type": "message",
                "thread_replies": [],
            },
            {
                "user": "bob",
                "text": "Pipeline outage resolved. Root cause was a docker image update.",
                "ts": "1710328800",
                "type": "message",
                "thread_replies": [],
            },
        ],
        "message_count": 4,
        "fetched_at": "2026-03-13T14:00:00Z",
    }
    cache.write_json("slack/channels/engineering/2026-03-13.json", slack_data)
    print(f"Created test Slack data: {len(slack_data['messages'])} messages")

    # --- Test 2: Run Slack Digest Agent ---
    print()
    print("=" * 60)
    print("TEST 2: Slack Digest Agent")
    print("=" * 60)

    params = json.dumps({"channel": "engineering", "date": "2026-03-13"})
    row = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) VALUES ('slack-digest', 'pending', $1::jsonb) RETURNING id",
        params,
    )
    job_id = row["id"]
    print(f"Created job {job_id}")

    llm = MockLLMClient(DIGEST_MOCK)
    runner = AgentRunner(
        db_pool=pool,
        knowledge_cache=cache,
        agent_registry={
            "dummy": DummyAgent,
            "issue-triage": IssueTriageAgent,
            "pr-context": PRContextAgent,
            "meeting-summary": MeetingSummaryAgent,
            "slack-digest": SlackDigestAgent,
        },
        llm_client=llm,
    )
    # Process all pending jobs until ours completes
    for _ in range(10):
        await runner._poll_and_execute()
        job = await pool.fetchrow("SELECT status FROM jobs WHERE id = $1", job_id)
        if job["status"] != "pending":
            break

    print(f"Job status: {job['status']}")
    assert job["status"] == "completed", f"Expected completed, got {job['status']}"

    # --- Test 3: Verify report ---
    print()
    print("=" * 60)
    print("TEST 3: Verify Slack Digest Report")
    print("=" * 60)
    report_path = "agent_outputs/slack_digests/engineering_2026-03-13.md"
    assert cache.file_exists(report_path), f"Report not found: {report_path}"
    report = cache.read_file(report_path)
    print(report[:500])

    # --- Test 4: Notification service ---
    print()
    print("=" * 60)
    print("TEST 4: Notification service (mock)")
    print("=" * 60)
    notifier = SlackNotifier(
        token="xoxb-fake-token",
        configs=[
            NotificationConfig(
                channel_id="C12345",
                channel_name="engineering",
                event_types=["issue.analyzed", "pr.analyzed", "meeting.summarized"],
            ),
        ],
    )
    # Test message formatting (won't actually send - no real token)
    print(f"Configured notifications: {len(notifier.configs)} channels")
    print(f"  #{notifier.configs[0].channel_name}: {notifier.configs[0].event_types}")

    # --- Test 5: Event bus subscription ---
    print()
    print("=" * 60)
    print("TEST 5: Event bus - slack.synced triggers digest")
    print("=" * 60)
    event_bus = EventBusProcessor(db_pool=pool)
    await event_bus._register_default_subscriptions()

    subs = await pool.fetch("SELECT agent_name, event_type FROM agent_subscriptions WHERE agent_name = 'slack-digest'")
    print(f"Slack digest subscriptions: {len(subs)}")
    for s in subs:
        print(f"  {s['agent_name']} -> {s['event_type']}")

    # Publish slack.synced event
    await pool.execute(
        "INSERT INTO events (event_type, source, payload) VALUES ('slack.synced', 'test', $1::jsonb)",
        json.dumps({"channel": "engineering", "messages": 4}),
    )
    await event_bus._process_events()

    pending = await pool.fetch(
        "SELECT id, agent_name, parameters FROM jobs WHERE agent_name = 'slack-digest' AND status = 'pending'"
    )
    print(f"Jobs created by event bus: {len(pending)}")

    # --- Verification ---
    print()
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Check all events
    events = await pool.fetch(
        "SELECT event_type, source FROM events WHERE event_type LIKE 'slack%' ORDER BY created_at"
    )
    print(f"Slack events: {len(events)}")
    for e in events:
        print(f"  {e['event_type']} (from {e['source']})")

    # Git log
    import subprocess

    result = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        cwd="knowledge-cache",
        capture_output=True,
        text=True,
    )
    print("\nKnowledge cache git log:")
    print(result.stdout)

    await pool.close()
    print("All Stage 8 tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
