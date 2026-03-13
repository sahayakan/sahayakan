"""Unit tests for the LLM client."""

import sys
sys.path.insert(0, "data-plane")

from llm_client.gemini_client import MockLLMClient


def test_mock_client_returns_response():
    client = MockLLMClient('{"result": "ok"}')
    resp = client.generate("test prompt")
    assert resp.text == '{"result": "ok"}'
    assert resp.model == "mock-model"
    assert resp.tokens_input > 0
    assert resp.tokens_output > 0
    assert resp.latency_ms == 50


def test_mock_client_records_calls():
    client = MockLLMClient("response")
    client.generate("prompt 1")
    client.generate("prompt 2")
    assert len(client.calls) == 2
    assert client.calls[0] == "prompt 1"


def test_mock_client_custom_model():
    client = MockLLMClient("test")
    resp = client.generate("prompt", model="custom-model")
    assert resp.model == "custom-model"


if __name__ == "__main__":
    test_mock_client_returns_response()
    test_mock_client_records_calls()
    test_mock_client_custom_model()
    print("All LLM client tests passed!")
