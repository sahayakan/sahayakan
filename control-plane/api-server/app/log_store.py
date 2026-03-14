"""In-memory log store with WebSocket broadcast support and DB persistence.

Stores log lines per job and allows WebSocket clients to subscribe
for real-time streaming. Persists logs to the job_logs table asynchronously.
"""

import asyncio
import contextlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

MAX_LINES_PER_JOB = 1000

_db_pool = None
_persist_queue: asyncio.Queue | None = None
_persist_task: asyncio.Task | None = None


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
_job_timestamps: dict[int, datetime] = {}

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
    _job_timestamps[job_id] = datetime.now(UTC)
    if len(logs) > MAX_LINES_PER_JOB:
        _logs[job_id] = logs[-MAX_LINES_PER_JOB:]

    # Broadcast to subscribers
    for queue in _subscribers.get(job_id, []):
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(entry)

    # Enqueue for DB persistence
    if _persist_queue is not None:
        with contextlib.suppress(asyncio.QueueFull):
            _persist_queue.put_nowait(entry)


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


def cleanup_stale_jobs(max_age_hours: int = 24) -> int:
    """Evict in-memory logs for jobs older than max_age_hours. Returns count evicted."""
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    stale = [jid for jid, ts in _job_timestamps.items() if ts < cutoff]
    for jid in stale:
        _logs.pop(jid, None)
        _job_timestamps.pop(jid, None)
    return len(stale)


async def _persist_worker() -> None:
    """Background worker that batch-inserts log entries into the DB."""
    while True:
        batch: list[LogEntry] = []
        try:
            # Wait for first entry
            entry = await _persist_queue.get()
            batch.append(entry)
            # Drain up to 49 more without blocking
            for _ in range(49):
                try:
                    entry = _persist_queue.get_nowait()
                    batch.append(entry)
                except asyncio.QueueEmpty:
                    break

            if _db_pool and batch:
                args = [(e.job_id, e.timestamp, e.level, e.message, e.stage) for e in batch]
                await _db_pool.executemany(
                    "INSERT INTO job_logs (job_id, timestamp, level, message, stage) "
                    "VALUES ($1, $2::timestamp, $3, $4, $5)",
                    args,
                )
        except asyncio.CancelledError:
            break
        except Exception:
            pass  # Best-effort persistence


def init_log_persistence(pool) -> None:
    """Start the background persist worker. Call after DB pool is ready."""
    global _db_pool, _persist_queue, _persist_task
    _db_pool = pool
    _persist_queue = asyncio.Queue(maxsize=5000)
    _persist_task = asyncio.create_task(_persist_worker())


async def get_logs_from_db(pool, job_id: int, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
    """Fetch logs from the DB for a given job_id. Returns (logs, total)."""
    total = await pool.fetchval("SELECT COUNT(*) FROM job_logs WHERE job_id = $1", job_id)
    rows = await pool.fetch(
        "SELECT timestamp, level, message, stage FROM job_logs "
        "WHERE job_id = $1 ORDER BY timestamp ASC OFFSET $2 LIMIT $3",
        job_id,
        offset,
        limit,
    )
    logs = [
        {
            "timestamp": str(r["timestamp"]),
            "job_id": job_id,
            "level": r["level"],
            "message": r["message"],
            "stage": r["stage"] or "",
        }
        for r in rows
    ]
    return logs, total
