"""Abstract LLM client interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_input: int
    tokens_output: int
    latency_ms: int


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str | None = None) -> LLMResponse:
        """Generate a response from the LLM."""
