from datetime import datetime

from pydantic import BaseModel


class JiraProjectCreate(BaseModel):
    name: str
    project_key: str
    base_url: str


class JiraProjectUpdate(BaseModel):
    name: str | None = None
    project_key: str | None = None
    base_url: str | None = None
    is_active: bool | None = None


class JiraProjectResponse(BaseModel):
    id: int
    name: str
    project_key: str
    base_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
