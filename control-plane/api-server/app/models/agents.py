from datetime import datetime

from pydantic import BaseModel


class AgentRegister(BaseModel):
    name: str
    version: str = "1.0"
    description: str | None = None
    container_image: str | None = None


class AgentResponse(BaseModel):
    id: int
    name: str
    version: str
    description: str | None
    container_image: str | None
    created_at: datetime
    updated_at: datetime
