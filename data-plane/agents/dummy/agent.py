"""Dummy agent for testing the full pipeline."""

from datetime import datetime, timezone

from agent_runner.contracts.base_agent import (
    AgentInput,
    AgentOutput,
    BaseAgent,
)
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger


class DummyAgent(BaseAgent):
    def __init__(self, knowledge_cache: KnowledgeCache, logger: AgentLogger):
        self.cache = knowledge_cache
        self.log = logger
        self.input: AgentInput | None = None

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        self.log.info(f"Loaded input: {agent_input.parameters}")

    def collect_context(self) -> None:
        self.log.info("Collecting context (no-op for dummy agent)")

    def analyze(self) -> None:
        self.log.info("Analyzing (no-op for dummy agent)")

    def generate_output(self) -> AgentOutput:
        self.log.info("Generating output")
        return AgentOutput(
            status="success",
            summary="Dummy agent test completed successfully",
            data={
                "agent": self.input.agent_name,
                "job_id": self.input.job_id,
                "parameters": self.input.parameters,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            artifacts=[
                {
                    "type": "test_report",
                    "path": f"agent_outputs/dummy/job_{self.input.job_id}.json",
                }
            ],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        uris = []
        for artifact in output.artifacts:
            path = artifact["path"]
            self.cache.write_json(path, output.data)
            uris.append(path)
            self.log.info(f"Stored artifact: {path}")
        return uris
