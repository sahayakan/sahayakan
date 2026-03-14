"""Structured JSON logging for the data-plane agent runner."""

import json
from datetime import UTC, datetime


class StructuredLogger:
    def __init__(self, component: str):
        self.component = component

    def _emit(self, level: str, message: str, **extra) -> None:
        entry = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": level,
            "component": self.component,
            "message": message,
        }
        if extra:
            entry.update(extra)
        print(json.dumps(entry), flush=True)

    def info(self, message: str, **extra) -> None:
        self._emit("INFO", message, **extra)

    def error(self, message: str, **extra) -> None:
        self._emit("ERROR", message, **extra)

    def warning(self, message: str, **extra) -> None:
        self._emit("WARNING", message, **extra)

    def debug(self, message: str, **extra) -> None:
        self._emit("DEBUG", message, **extra)


def get_logger(component: str) -> StructuredLogger:
    return StructuredLogger(component)
