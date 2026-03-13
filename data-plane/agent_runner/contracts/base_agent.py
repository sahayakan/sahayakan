from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentInput:
    job_id: int
    agent_name: str
    source: str
    parameters: dict


@dataclass
class AgentOutput:
    status: str  # "success" or "error"
    summary: str
    data: dict
    artifacts: list[dict] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class that all agents must implement.

    The runner enforces execution order:
        load_input -> collect_context -> analyze -> generate_output -> store_artifacts
    """

    @abstractmethod
    def load_input(self, agent_input: AgentInput) -> None:
        """Load and validate input data."""

    @abstractmethod
    def collect_context(self) -> None:
        """Gather related context from knowledge cache."""

    @abstractmethod
    def analyze(self) -> None:
        """Perform LLM-powered analysis."""

    @abstractmethod
    def generate_output(self) -> AgentOutput:
        """Produce structured output."""

    @abstractmethod
    def store_artifacts(self, output: AgentOutput) -> list[str]:
        """Store artifacts in knowledge cache and/or MinIO. Returns list of URIs."""
