"""Gemini LLM client via Vertex AI."""

import time

from .base import LLMClient, LLMResponse


class GeminiClient(LLMClient):
    DEFAULT_MODEL = "gemini-1.5-pro"
    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # seconds

    def __init__(self, project: str, location: str = "us-central1"):
        self.project = project
        self.location = location
        self._model_cache: dict = {}

    def _get_model(self, model_name: str):
        if model_name not in self._model_cache:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project, location=self.location)
            self._model_cache[model_name] = GenerativeModel(model_name)
        return self._model_cache[model_name]

    def generate(self, prompt: str, model: str | None = None) -> LLMResponse:
        model_name = model or self.DEFAULT_MODEL
        gen_model = self._get_model(model_name)

        last_exception = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start = time.monotonic()
                response = gen_model.generate_content(prompt)
                latency_ms = int((time.monotonic() - start) * 1000)

                usage = response.usage_metadata
                return LLMResponse(
                    text=response.text,
                    model=model_name,
                    tokens_input=usage.prompt_token_count,
                    tokens_output=usage.candidates_token_count,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.BACKOFF_BASE**attempt
                    time.sleep(wait)

        raise last_exception


class MockLLMClient(LLMClient):
    """Mock client for testing without Vertex AI credentials."""

    def __init__(self, response_text: str = '{"status": "success"}'):
        self.response_text = response_text
        self.calls: list[str] = []

    def generate(self, prompt: str, model: str | None = None) -> LLMResponse:
        self.calls.append(prompt)
        return LLMResponse(
            text=self.response_text,
            model=model or "mock-model",
            tokens_input=len(prompt.split()),
            tokens_output=len(self.response_text.split()),
            latency_ms=50,
        )
