"""Job Scheduler Service.

Polls the schedules table and creates jobs/triggers ingestion
when cron expressions match the current time.
"""

import asyncio
import json
from datetime import datetime, timezone

import asyncpg

from scheduler.cron import cron_matches, next_run_after


class SchedulerService:
    POLL_INTERVAL = 30  # seconds - check every 30s

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.running = False

    async def start(self) -> None:
        self.running = True
        print("[Scheduler] Started", flush=True)
        # Compute initial next_run_at for schedules that don't have one
        await self._initialize_next_runs()
        while self.running:
            try:
                await self._check_schedules()
            except Exception as e:
                print(f"[Scheduler] Error: {e}", flush=True)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def stop(self) -> None:
        self.running = False
        print("[Scheduler] Stopped", flush=True)

    async def _initialize_next_runs(self) -> None:
        """Set next_run_at for schedules that don't have one."""
        rows = await self.pool.fetch(
            "SELECT id, cron_expression FROM schedules "
            "WHERE enabled = TRUE AND next_run_at IS NULL"
        )
        now = datetime.utcnow()
        for row in rows:
            next_run = next_run_after(row["cron_expression"], now)
            await self.pool.execute(
                "UPDATE schedules SET next_run_at = $2 WHERE id = $1",
                row["id"],
                next_run,
            )
        if rows:
            print(f"[Scheduler] Initialized {len(rows)} schedule(s)", flush=True)

    async def _check_schedules(self) -> None:
        """Check for due schedules and execute them."""
        now = datetime.utcnow()

        # Find schedules that are due
        due = await self.pool.fetch(
            "SELECT id, name, agent_name, schedule_type, cron_expression, parameters "
            "FROM schedules "
            "WHERE enabled = TRUE AND next_run_at <= $1 "
            "ORDER BY next_run_at ASC",
            now,
        )

        for schedule in due:
            schedule_id = schedule["id"]
            name = schedule["name"]
            schedule_type = schedule["schedule_type"]
            params = schedule["parameters"]
            if isinstance(params, str):
                params = json.loads(params)
            params = params or {}

            print(f"[Scheduler] Triggering: {name} ({schedule_type})", flush=True)

            try:
                if schedule_type == "agent_job":
                    await self._create_agent_job(
                        schedule["agent_name"], params
                    )
                elif schedule_type == "github_sync":
                    await self._publish_event(
                        "github.sync_requested", "scheduler", params
                    )
                elif schedule_type == "jira_sync":
                    await self._publish_event(
                        "jira.sync_requested", "scheduler", params
                    )
                elif schedule_type == "slack_sync":
                    await self._publish_event(
                        "slack.sync_requested", "scheduler", params
                    )
                else:
                    print(
                        f"[Scheduler] Unknown type: {schedule_type}",
                        flush=True,
                    )
            except Exception as e:
                print(f"[Scheduler] Failed {name}: {e}", flush=True)

            # Update last_run and compute next_run
            next_run = next_run_after(schedule["cron_expression"], now)
            await self.pool.execute(
                "UPDATE schedules SET last_run_at = $2, next_run_at = $3 "
                "WHERE id = $1",
                schedule_id,
                now,
                next_run,
            )

    async def _create_agent_job(self, agent_name: str, params: dict) -> None:
        """Create a job for an agent."""
        await self.pool.execute(
            "INSERT INTO jobs (agent_name, status, parameters) "
            "VALUES ($1, 'pending', $2::jsonb)",
            agent_name,
            json.dumps(params),
        )

    async def _publish_event(
        self, event_type: str, source: str, payload: dict
    ) -> None:
        """Publish an event to the event bus."""
        await self.pool.execute(
            "INSERT INTO events (event_type, source, payload) "
            "VALUES ($1, $2, $3::jsonb)",
            event_type,
            source,
            json.dumps(payload),
        )
