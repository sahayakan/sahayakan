from datetime import datetime

from pydantic import BaseModel


class RepositoryCreate(BaseModel):
    name: str
    url: str
    provider: str = "github"
    default_branch: str = "main"


class RepositoryUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    provider: str | None = None
    default_branch: str | None = None
    is_active: bool | None = None


class RepositoryResponse(BaseModel):
    id: int
    name: str
    url: str
    provider: str
    default_branch: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
