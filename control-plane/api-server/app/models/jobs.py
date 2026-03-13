from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobCreate(BaseModel):
    agent: str
    parameters: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: int
    agent_name: str
    status: str
    parameters: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
