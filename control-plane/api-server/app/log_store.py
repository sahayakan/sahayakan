"""In-memory log store with WebSocket broadcast support.

Stores log lines per job and allows WebSocket clients to subscribe
for real-time streaming.
"""

import asyncio
import contextlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

MAX_LINES_PER_JOB = 1000


@dataclass
class LogEntry:
    timestamp: str
    job_id: int
    level: str
    message: str
    stage: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "level": self.level,
            "message": self.message,
            "stage": self.stage,
        }


# Module-level singleton
_logs: dict[int, list[LogEntry]] = defaultdict(list)
_subscribers: dict[int, list[asyncio.Queue]] = defaultdict(list)

# Pattern to parse structured log lines from the runner
_LOG_PATTERN = re.compile(r"\[(\w+)\]\s+\[([^\]]+)\]\s+\[(\d+)\]\s+(.*)")


def parse_log_line(line: str) -> LogEntry | None:
    m = _LOG_PATTERN.match(line.strip())
    if not m:
        return None
    level, timestamp, job_id, message = m.groups()
    return LogEntry(
        timestamp=timestamp,
        job_id=int(job_id),
        level=level,
        message=message,
    )


def add_log(job_id: int, entry: LogEntry) -> None:
    logs = _logs[job_id]
    logs.append(entry)
    if len(logs) > MAX_LINES_PER_JOB:
        _logs[job_id] = logs[-MAX_LINES_PER_JOB:]

    # Broadcast to subscribers
    for queue in _subscribers.get(job_id, []):
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(entry)


def add_log_line(job_id: int, level: str, message: str, stage: str = "") -> None:
    entry = LogEntry(
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        job_id=job_id,
        level=level,
        message=message,
        stage=stage,
    )
    add_log(job_id, entry)


def get_logs(job_id: int, offset: int = 0, limit: int = 100) -> list[dict]:
    logs = _logs.get(job_id, [])
    return [e.to_dict() for e in logs[offset : offset + limit]]


def get_log_count(job_id: int) -> int:
    return len(_logs.get(job_id, []))


def subscribe(job_id: int) -> asyncio.Queue:
    queue = asyncio.Queue(maxsize=200)
    _subscribers[job_id].append(queue)
    return queue


def unsubscribe(job_id: int, queue: asyncio.Queue) -> None:
    subs = _subscribers.get(job_id, [])
    if queue in subs:
        subs.remove(queue)
    if not subs and job_id in _subscribers:
        del _subscribers[job_id]
