"""End-to-end test for Stage 10: Insights Engine."""

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
from agents.slack_digest.agent import SlackDigestAgent
from agents.insights.agent import InsightsAgent
from agents.trend_analysis.agent import TrendAnalysisAgent
from llm_client.gemini_client import MockLLMClient

INSIGHTS_MOCK = json.dumps({
    "insights": [
        {
            "insight_type": "recurring_bug",
            "title": "Repeated shell completion issues",
            "description": "Multiple issues related to shell completion context handling detected across recent analyses.",
            "evidence": [
                {"type": "issue", "id": 2800, "detail": "Context cleanup in shell completion"},
            ],
            "severity": "medium",
            "confidence": 0.72,
        },
        {
            "insight_type": "process_gap",
            "title": "Action items not tracked in Jira",
            "description": "Meeting action items reference GitHub issues but not Jira tickets, suggesting a gap in project tracking.",
            "evidence": [
                {"type": "meeting", "id": "2026-03-13-standup", "detail": "Action items without Jira references"},
            ],
            "severity": "low",
            "confidence": 0.61,
        },
    ]
})

TRENDS_MOCK = json.dumps({
    "summary": "Development activity is steady with moderate risk levels. Shell completion area shows recurring issues.",
    "issue_trends": [
        {"component": "shell-completion", "trend": "increasing", "detail": "Multiple related issues in recent period"},
    ],
    "risk_areas": ["shell-completion", "context-management"],
    "positive_signals": ["PR review process working well", "Meeting action items being tracked"],
    "recommendations": [
        "Prioritize shell completion fixes",
        "Add Jira tracking for meeting action items",
    ],
    "health_score": 0.72,
})


async def main():
    pool = await asyncpg.create_pool(
        user="sahayakan", password="sahayakan_dev_password",
        database="sahayakan", host="localhost", port=5433,
        min_size=1, max_size=5,
    )
    cache = KnowledgeCache("knowledge-cache")
    registry = {
        "dummy": DummyAgent, "issue-triage": IssueTriageAgent,
        "pr-context": PRContextAgent, "meeting-summary": MeetingSummaryAgent,
        "slack-digest": SlackDigestAgent, "insights": InsightsAgent,
        "trend-analysis": TrendAnalysisAgent,
    }

    for name, desc in [("insights", "Detects patterns"), ("trend-analysis", "Produces trend reports")]:
        await pool.execute(
            "INSERT INTO agents (name, version, description) "
            "VALUES ($1, '1.0', $2) ON CONFLICT (name) DO NOTHING",
            name, desc,
        )

    # --- Test 1: Insights Agent ---
    print("=" * 60)
    print("TEST 1: Insights Agent")
    print("=" * 60)
    params = json.dumps({"source": "scheduled"})
    row = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) "
        "VALUES ('insights', 'pending', $1::jsonb) RETURNING id", params,
    )
    llm = MockLLMClient(INSIGHTS_MOCK)
    runner = AgentRunner(db_pool=pool, knowledge_cache=cache, agent_registry=registry, llm_client=llm)

    for _ in range(10):
        await runner._poll_and_execute()
        job = await pool.fetchrow("SELECT status FROM jobs WHERE id = $1", row["id"])
        if job["status"] != "pending":
            break
    print(f"Insights job status: {job['status']}")
    assert job["status"] == "completed"

    # Store insights in DB
    report = cache.read_json(f"agent_outputs/insights/{__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')}.json")
    for ins in report.get("insights", []):
        await pool.execute(
            "INSERT INTO insights (insight_type, title, description, evidence, severity, confidence) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
            ins["insight_type"], ins["title"], ins["description"],
            json.dumps(ins.get("evidence", [])), ins["severity"], ins["confidence"],
        )
    print(f"Stored {len(report.get('insights', []))} insights in database")

    # --- Test 2: Trend Analysis Agent ---
    print()
    print("=" * 60)
    print("TEST 2: Trend Analysis Agent")
    print("=" * 60)
    params2 = json.dumps({"source": "scheduled"})
    row2 = await pool.fetchrow(
        "INSERT INTO jobs (agent_name, status, parameters) "
        "VALUES ('trend-analysis', 'pending', $1::jsonb) RETURNING id", params2,
    )
    llm2 = MockLLMClient(TRENDS_MOCK)
    runner2 = AgentRunner(db_pool=pool, knowledge_cache=cache, agent_registry=registry, llm_client=llm2)

    for _ in range(10):
        await runner2._poll_and_execute()
        job2 = await pool.fetchrow("SELECT status FROM jobs WHERE id = $1", row2["id"])
        if job2["status"] != "pending":
            break
    print(f"Trend analysis job status: {job2['status']}")
    assert job2["status"] == "completed"

    # --- Test 3: API endpoints ---
    print()
    print("=" * 60)
    print("TEST 3: Insights API")
    print("=" * 60)
    import urllib.request

    resp = urllib.request.urlopen("http://localhost:8000/insights?status=active")
    insights_data = json.loads(resp.read())
    print(f"Active insights: {len(insights_data['insights'])}")
    for ins in insights_data["insights"]:
        print(f"  [{ins['severity']}] {ins['title']} (confidence: {ins['confidence']})")

    resp = urllib.request.urlopen("http://localhost:8000/insights/summary")
    summary = json.loads(resp.read())
    print(f"\nInsights summary: {summary}")

    resp = urllib.request.urlopen("http://localhost:8000/insights/trends")
    trends = json.loads(resp.read())
    print(f"Trend data: {len(trends['job_trends'])} job entries, {len(trends['usage_trends'])} usage entries")

    # --- Test 4: Acknowledge insight ---
    print()
    print("=" * 60)
    print("TEST 4: Acknowledge insight")
    print("=" * 60)
    if insights_data["insights"]:
        ins_id = insights_data["insights"][0]["id"]
        req = urllib.request.Request(
            f"http://localhost:8000/insights/{ins_id}/status",
            data=json.dumps({"status": "acknowledged"}).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        resp = urllib.request.urlopen(req)
        updated = json.loads(resp.read())
        print(f"Insight #{ins_id} status: {updated['status']}")

    # --- Verification ---
    print()
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    for path in [
        f"agent_outputs/insights/{__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')}.md",
        f"agent_outputs/trends/{__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')}.md",
    ]:
        exists = cache.file_exists(path)
        print(f"{'OK' if exists else 'MISSING'}: {path}")

    import subprocess
    result = subprocess.run(["git", "log", "--oneline", "-3"], cwd="knowledge-cache", capture_output=True, text=True)
    print(f"\nKnowledge cache git log:\n{result.stdout}")

    await pool.close()
    print("All Stage 10 tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
