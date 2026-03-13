"""Structured logging for agents and the runner."""

import sys
from datetime import datetime, timezone


class AgentLogger:
    def __init__(self, job_id: int | None = None):
        self.job_id = job_id
        self._lines: list[str] = []

    def _format(self, level: str, message: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        job_part = f" [{self.job_id}]" if self.job_id is not None else ""
        return f"[{level}]  [{ts}]{job_part} {message}"

    def _emit(self, line: str) -> None:
        self._lines.append(line)
        print(line, flush=True)

    def info(self, message: str) -> None:
        self._emit(self._format("INFO", message))

    def error(self, message: str) -> None:
        self._emit(self._format("ERROR", message))

    def llm(self, model: str, tokens: int, latency_ms: int) -> None:
        msg = f"model={model} tokens={tokens} latency={latency_ms}ms"
        self._emit(self._format("LLM", msg))

    def gate(self, stage: str, status: str) -> None:
        msg = f"stage={stage} status={status}"
        self._emit(self._format("GATE", msg))

    def get_lines(self) -> list[str]:
        return list(self._lines)
