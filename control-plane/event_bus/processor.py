"""Event Bus Processor - polls events table and triggers subscribed agents."""

import asyncio
import json
from datetime import datetime, timezone

import asyncpg


class EventBusProcessor:
    POLL_INTERVAL = 3  # seconds

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.running = False

    async def start(self) -> None:
        self.running = True
        print("[EventBus] Started polling for events", flush=True)
        await self._register_default_subscriptions()
        while self.running:
            try:
                await self._process_events()
            except Exception as e:
                print(f"[EventBus] Error: {e}", flush=True)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def stop(self) -> None:
        self.running = False
        print("[EventBus] Stopped", flush=True)

    async def _register_default_subscriptions(self) -> None:
        """Register default event subscriptions for MVP agents."""
        defaults = [
            ("issue-triage", "issue.ingested"),
            ("pr-context", "pr.ingested"),
            ("pr-context", "issue.analyzed"),
            ("meeting-summary", "meeting.uploaded"),
            ("slack-digest", "slack.synced"),
        ]
        for agent_name, event_type in defaults:
            # Only register if agent exists
            agent = await self.pool.fetchrow(
                "SELECT name FROM agents WHERE name = $1", agent_name
            )
            if agent:
                await self.pool.execute(
                    "INSERT INTO agent_subscriptions (agent_name, event_type) "
                    "VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    agent_name,
                    event_type,
                )
        print("[EventBus] Default subscriptions registered", flush=True)

    async def _process_events(self) -> None:
        # Fetch unprocessed events
        events = await self.pool.fetch(
            "SELECT id, event_type, source, payload, created_at "
            "FROM events WHERE processed = FALSE "
            "ORDER BY created_at ASC LIMIT 20"
        )

        for event in events:
            event_id = event["id"]
            event_type = event["event_type"]
            payload = event["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            # Find subscribed agents
            subs = await self.pool.fetch(
                "SELECT agent_name FROM agent_subscriptions "
                "WHERE event_type = $1",
                event_type,
            )

            for sub in subs:
                agent_name = sub["agent_name"]
                # Build job parameters from event payload
                job_params = self._build_job_params(
                    agent_name, event_type, payload
                )
                if job_params is None:
                    continue

                # Check for duplicate jobs (avoid re-triggering)
                existing = await self.pool.fetchrow(
                    "SELECT id FROM jobs WHERE agent_name = $1 "
                    "AND parameters::text = $2 "
                    "AND status IN ('pending', 'running')",
                    agent_name,
                    json.dumps(job_params),
                )
                if existing:
                    continue

                # Create job
                await self.pool.execute(
                    "INSERT INTO jobs (agent_name, status, parameters) "
                    "VALUES ($1, 'pending', $2::jsonb)",
                    agent_name,
                    json.dumps(job_params),
                )
                print(
                    f"[EventBus] Event '{event_type}' -> "
                    f"created job for '{agent_name}'",
                    flush=True,
                )

            # Mark event as processed
            await self.pool.execute(
                "UPDATE events SET processed = TRUE WHERE id = $1",
                event_id,
            )

    def _build_job_params(
        self, agent_name: str, event_type: str, payload: dict
    ) -> dict | None:
        """Build appropriate job parameters based on agent and event."""
        if agent_name == "issue-triage" and event_type == "issue.ingested":
            issue_id = payload.get("issue_id") or payload.get("issue_number")
            if issue_id:
                return {"issue_id": issue_id, "source": "event"}
        elif agent_name == "pr-context" and event_type == "pr.ingested":
            pr_number = payload.get("pr_number")
            if pr_number:
                return {"pr_number": pr_number, "source": "event"}
        elif agent_name == "pr-context" and event_type == "issue.analyzed":
            # When an issue is analyzed, check if there are related PRs
            # The issue analysis event may contain related PR info
            pr_number = payload.get("pr_number")
            if pr_number:
                return {"pr_number": pr_number, "source": "event"}
            # Otherwise skip - no PR to analyze
            return None
        elif agent_name == "meeting-summary" and event_type == "meeting.uploaded":
            transcript_id = payload.get("transcript_id")
            if transcript_id:
                return {"transcript_id": transcript_id, "source": "event"}
        elif agent_name == "slack-digest" and event_type == "slack.synced":
            channel = payload.get("channel")
            if channel:
                return {"channel": channel, "source": "event"}

        return None
