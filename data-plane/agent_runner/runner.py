"""Agent runner - polls for pending jobs and executes agents."""

import asyncio
import json
import traceback

import asyncpg

from agent_runner.contracts.base_agent import AgentInput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger


class AgentRunner:
    POLL_INTERVAL = 5  # seconds
    REVIEW_POLL_INTERVAL = 3  # seconds

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        knowledge_cache: KnowledgeCache,
        agent_registry: dict[str, type],
        llm_client=None,
        embedding_service=None,
    ):
        self.pool = db_pool
        self.cache = knowledge_cache
        self.agent_registry = agent_registry
        self.llm_client = llm_client
        self.embedding_service = embedding_service
        self.running = False

    async def start(self) -> None:
        self.running = True
        print("[Runner] Started polling for jobs", flush=True)
        while self.running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                print(f"[Runner] Poll error: {e}", flush=True)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def stop(self) -> None:
        self.running = False
        print("[Runner] Stopped", flush=True)

    async def _poll_and_execute(self) -> None:
        row = await self.pool.fetchrow(
            "UPDATE jobs SET status = 'running', started_at = NOW() "
            "WHERE id = (SELECT id FROM jobs WHERE status = 'pending' "
            "ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED) "
            "RETURNING id, agent_name, parameters"
        )
        if not row:
            return

        job_id = row["id"]
        agent_name = row["agent_name"]
        parameters = row["parameters"] or {}
        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        logger = AgentLogger(job_id=job_id)
        logger.info(f"Picked up job {job_id} for agent '{agent_name}'")

        # Create agent run record
        run_row = await self.pool.fetchrow(
            "INSERT INTO agent_runs (job_id, agent_name, status) "
            "VALUES ($1, $2, 'started') RETURNING id",
            job_id,
            agent_name,
        )
        run_id = run_row["id"]

        try:
            agent = self._load_agent(agent_name, logger)
            agent_input = AgentInput(
                job_id=job_id,
                agent_name=agent_name,
                source=parameters.get("source", "api"),
                parameters=parameters,
            )

            # Stage 1: Load input
            await self._update_run_status(run_id, "collecting_data")
            logger.info("Loading input")
            agent.load_input(agent_input)
            await self._check_review_gate(
                job_id, run_id, agent_name, "after_input", logger
            )

            # Stage 2: Collect context
            logger.info("Collecting context")
            agent.collect_context()
            await self._check_review_gate(
                job_id, run_id, agent_name, "after_context", logger
            )

            # Stage 3: Analyze
            await self._update_run_status(run_id, "analyzing")
            logger.info("Analyzing")
            agent.analyze()
            await self._check_review_gate(
                job_id, run_id, agent_name, "after_analysis", logger
            )

            # Stage 4: Generate output
            await self._update_run_status(run_id, "generating_output")
            logger.info("Generating output")
            output = agent.generate_output()
            await self._check_review_gate(
                job_id, run_id, agent_name, "after_output", logger
            )

            # Stage 5: Store artifacts
            await self._update_run_status(run_id, "storing_artifacts")
            logger.info("Storing artifacts")
            uris = agent.store_artifacts(output)

            # Commit to knowledge cache
            commit_hash = self.cache.commit(
                message=output.summary,
                files=uris,
                agent_name=agent_name,
                job_id=job_id,
                source=agent_input.source,
            )
            logger.info(f"Committed to knowledge cache: {commit_hash[:8]}")

            # Record artifacts in database
            for uri in uris:
                await self.pool.execute(
                    "INSERT INTO artifacts (run_id, artifact_type, storage_uri) "
                    "VALUES ($1, $2, $3)",
                    run_id,
                    "agent_output",
                    uri,
                )

            # Record LLM usage if available
            llm_usage = output.data.get("llm_usage") if output.data else None
            if llm_usage:
                await self.pool.execute(
                    "INSERT INTO llm_usage "
                    "(run_id, model, tokens_input, tokens_output, latency_ms) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    run_id,
                    llm_usage.get("model", "unknown"),
                    llm_usage.get("tokens_input", 0),
                    llm_usage.get("tokens_output", 0),
                    llm_usage.get("latency_ms", 0),
                )

            # Complete run and job
            await self._update_run_status(
                run_id, "completed", git_commit=commit_hash
            )
            await self._update_job_status(job_id, "completed")
            logger.info(f"Job {job_id} completed successfully")

            # Publish event
            await self._publish_event(agent_name, job_id, output)

        except ReviewRejectedException as e:
            logger.error(f"Job {job_id} rejected at review: {e}")
            await self._update_run_status(run_id, "failed")
            await self._update_job_status(job_id, "failed")

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Job {job_id} failed: {e}\n{tb}")
            await self._update_run_status(run_id, "failed")
            await self._update_job_status(job_id, "failed")

    def _load_agent(self, agent_name: str, logger: AgentLogger) -> BaseAgent:
        agent_cls = self.agent_registry.get(agent_name)
        if not agent_cls:
            raise ValueError(f"Unknown agent: {agent_name}")
        # Build kwargs based on what the agent constructor accepts
        import inspect
        sig = inspect.signature(agent_cls.__init__)
        kwargs = {"knowledge_cache": self.cache, "logger": logger}
        if "llm_client" in sig.parameters:
            kwargs["llm_client"] = self.llm_client
        if "embedding_service" in sig.parameters:
            kwargs["embedding_service"] = self.embedding_service
        return agent_cls(**kwargs)

    async def _update_run_status(
        self, run_id: int, status: str, git_commit: str | None = None
    ) -> None:
        if status in ("completed", "failed"):
            await self.pool.execute(
                "UPDATE agent_runs SET status = $2::run_status, end_time = NOW(), "
                "git_commit = COALESCE($3, git_commit) WHERE id = $1",
                run_id,
                status,
                git_commit,
            )
        else:
            await self.pool.execute(
                "UPDATE agent_runs SET status = $2::run_status WHERE id = $1",
                run_id,
                status,
            )

    async def _update_job_status(self, job_id: int, status: str) -> None:
        if status == "completed":
            await self.pool.execute(
                "UPDATE jobs SET status = $2::job_status, completed_at = NOW() "
                "WHERE id = $1",
                job_id,
                status,
            )
        else:
            await self.pool.execute(
                "UPDATE jobs SET status = $2::job_status WHERE id = $1",
                job_id,
                status,
            )

    async def _check_review_gate(
        self,
        job_id: int,
        run_id: int,
        agent_name: str,
        stage: str,
        logger: AgentLogger,
    ) -> None:
        gate = await self.pool.fetchrow(
            "SELECT enabled FROM review_gates "
            "WHERE agent_name = $1 AND stage = $2",
            agent_name,
            stage,
        )
        if not gate or not gate["enabled"]:
            return

        logger.gate(stage, "awaiting_review")
        await self._update_run_status(run_id, "awaiting_review")
        await self._update_job_status(job_id, "awaiting_review")

        # Poll until a review decision is made
        while True:
            decision = await self.pool.fetchrow(
                "SELECT decision, comments FROM review_decisions "
                "WHERE run_id = $1 AND stage = $2 "
                "ORDER BY decided_at DESC LIMIT 1",
                run_id,
                stage,
            )
            if decision:
                if decision["decision"] == "approved":
                    logger.gate(stage, "approved")
                    await self._update_run_status(run_id, "started")
                    await self._update_job_status(job_id, "running")
                    return
                else:
                    raise ReviewRejectedException(
                        f"Rejected at {stage}: "
                        f"{decision['comments'] or 'No reason given'}"
                    )
            await asyncio.sleep(self.REVIEW_POLL_INTERVAL)

    async def _publish_event(self, agent_name: str, job_id: int, output) -> None:
        # Map agent names to semantic event types
        event_type_map = {
            "issue-triage": "issue.analyzed",
            "pr-context": "pr.analyzed",
            "meeting-summary": "meeting.summarized",
        }
        event_type = event_type_map.get(
            agent_name, f"{agent_name}.completed"
        )
        payload = {
            "job_id": job_id,
            "agent": agent_name,
            "status": output.status,
            "summary": output.summary,
        }
        # Include key data from the output
        if output.data:
            for key in (
                "issue_number", "pr_number", "meeting_id",
                "priority", "confidence",
            ):
                if key in output.data:
                    payload[key] = output.data[key]
        await self.pool.execute(
            "INSERT INTO events (event_type, source, payload) "
            "VALUES ($1, $2, $3::jsonb)",
            event_type,
            agent_name,
            json.dumps(payload),
        )


class ReviewRejectedException(Exception):
    pass
