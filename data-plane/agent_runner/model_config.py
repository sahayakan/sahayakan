"""Per-agent LLM model configuration.

Configures which Gemini model each agent uses and token budgets.
Pro for deep analysis, Flash for fast summaries.
"""

AGENT_MODEL_CONFIG = {
    "issue-triage": {
        "model": "gemini-1.5-pro",
        "max_tokens_per_call": 4000,
        "max_llm_calls": 5,
        "max_runtime_seconds": 300,
    },
    "pr-context": {
        "model": "gemini-1.5-pro",
        "max_tokens_per_call": 8000,
        "max_llm_calls": 10,
        "max_runtime_seconds": 600,
    },
    "meeting-summary": {
        "model": "gemini-1.5-pro",
        "max_tokens_per_call": 16000,
        "max_llm_calls": 5,
        "max_runtime_seconds": 600,
    },
    "slack-digest": {
        "model": "gemini-1.5-flash",
        "max_tokens_per_call": 12000,
        "max_llm_calls": 5,
        "max_runtime_seconds": 300,
    },
    "insights": {
        "model": "gemini-1.5-pro",
        "max_tokens_per_call": 8000,
        "max_llm_calls": 3,
        "max_runtime_seconds": 600,
    },
    "trend-analysis": {
        "model": "gemini-1.5-flash",
        "max_tokens_per_call": 4000,
        "max_llm_calls": 3,
        "max_runtime_seconds": 300,
    },
}

DEFAULT_CONFIG = {
    "model": "gemini-1.5-pro",
    "max_tokens_per_call": 4000,
    "max_llm_calls": 5,
    "max_runtime_seconds": 300,
}


def get_model_for_agent(agent_name: str) -> str:
    return AGENT_MODEL_CONFIG.get(agent_name, DEFAULT_CONFIG)["model"]


def get_config_for_agent(agent_name: str) -> dict:
    return AGENT_MODEL_CONFIG.get(agent_name, DEFAULT_CONFIG)
