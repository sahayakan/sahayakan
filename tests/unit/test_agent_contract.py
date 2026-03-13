"""Unit tests for agent contract compliance."""

import sys
import tempfile

sys.path.insert(0, "data-plane")

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from agents.dummy.agent import DummyAgent
from agents.issue_triage.agent import IssueTriageAgent
from agents.meeting_summary.agent import MeetingSummaryAgent
from agents.pr_context.agent import PRContextAgent


def test_all_agents_are_base_agent():
    """All agents must inherit from BaseAgent."""
    for cls in [DummyAgent, IssueTriageAgent, PRContextAgent, MeetingSummaryAgent]:
        assert issubclass(cls, BaseAgent), f"{cls.__name__} must inherit BaseAgent"


def test_all_agents_implement_methods():
    """All agents must implement all abstract methods."""
    required = {"load_input", "collect_context", "analyze", "generate_output", "store_artifacts"}
    for cls in [DummyAgent, IssueTriageAgent, PRContextAgent, MeetingSummaryAgent]:
        methods = {m for m in dir(cls) if not m.startswith("_")}
        missing = required - methods
        assert not missing, f"{cls.__name__} missing methods: {missing}"


def test_dummy_agent_full_lifecycle():
    """DummyAgent completes the full lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        logger = AgentLogger(job_id=999)
        agent = DummyAgent(knowledge_cache=cache, logger=logger)

        inp = AgentInput(job_id=999, agent_name="dummy", source="test", parameters={"test": True})
        agent.load_input(inp)
        agent.collect_context()
        agent.analyze()
        output = agent.generate_output()
        assert isinstance(output, AgentOutput)
        assert output.status == "success"

        uris = agent.store_artifacts(output)
        assert len(uris) > 0


def test_agent_output_dataclass():
    output = AgentOutput(status="success", summary="test", data={"key": "val"})
    assert output.status == "success"
    assert output.artifacts == []  # Default empty list


if __name__ == "__main__":
    test_all_agents_are_base_agent()
    test_all_agents_implement_methods()
    test_dummy_agent_full_lifecycle()
    test_agent_output_dataclass()
    print("All agent contract tests passed!")
