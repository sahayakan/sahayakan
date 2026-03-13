from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    event_type: str
    source: str
    payload: dict[str, Any] | None
    created_at: datetime
    processed: bool
