"""Structured logging for agents and the runner."""

from datetime import UTC, datetime


class AgentLogger:
    def __init__(self, job_id: int | None = None, request_id: str = ""):
        self.job_id = job_id
        self.request_id = request_id
        self._lines: list[str] = []

    def _format(self, level: str, message: str) -> str:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        job_part = f" [{self.job_id}]" if self.job_id is not None else ""
        req_part = f" [req:{self.request_id}]" if self.request_id else ""
        return f"[{level}]  [{ts}]{job_part}{req_part} {message}"

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
