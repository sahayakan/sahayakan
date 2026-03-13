"""Minimal cron expression parser.

Supports: minute hour day_of_month month day_of_week
Values: number, *, */N, comma-separated
"""

from datetime import datetime


def _match_field(field: str, value: int, max_val: int) -> bool:
    """Check if a cron field matches a given value."""
    if field == "*":
        return True
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/", 1)
            step = int(step)
            if base == "*":
                if value % step == 0:
                    return True
            else:
                base_val = int(base)
                if value >= base_val and (value - base_val) % step == 0:
                    return True
        elif "-" in part:
            lo, hi = part.split("-", 1)
            if int(lo) <= value <= int(hi):
                return True
        else:
            if int(part) == value:
                return True
    return False


def cron_matches(expression: str, dt: datetime) -> bool:
    """Check if a cron expression matches the given datetime.

    Format: minute hour day_of_month month day_of_week
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expression}")

    minute, hour, dom, month, dow = parts
    return (
        _match_field(minute, dt.minute, 59)
        and _match_field(hour, dt.hour, 23)
        and _match_field(dom, dt.day, 31)
        and _match_field(month, dt.month, 12)
        and _match_field(dow, dt.isoweekday() % 7, 6)  # 0=Sun
    )


def next_run_after(expression: str, after: datetime) -> datetime:
    """Find the next datetime that matches the cron expression.

    Scans minute by minute (up to 48h ahead).
    Returns a naive (no timezone) datetime for DB compatibility.
    """
    from datetime import timedelta

    # Work with naive datetime
    dt = after.replace(second=0, microsecond=0, tzinfo=None) + timedelta(minutes=1)
    for _ in range(48 * 60):  # Max 48 hours ahead
        if cron_matches(expression, dt):
            return dt
        dt += timedelta(minutes=1)
    return dt  # Fallback
