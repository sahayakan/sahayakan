from datetime import datetime

from pydantic import BaseModel


class GitHubAppCreate(BaseModel):
    app_id: int
    app_name: str
    private_key: str
    webhook_secret: str | None = None


class GitHubAppUpdate(BaseModel):
    app_name: str | None = None
    private_key: str | None = None
    webhook_secret: str | None = None


class GitHubAppResponse(BaseModel):
    id: int
    app_id: int
    app_name: str
    webhook_secret: str | None
    created_at: datetime
    updated_at: datetime


class InstallationCreate(BaseModel):
    installation_id: int
    account_login: str
    account_type: str = "Organization"


class InstallationResponse(BaseModel):
    id: int
    github_app_id: int
    installation_id: int
    account_login: str
    account_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DiscoveredRepo(BaseModel):
    name: str
    url: str
    default_branch: str


class DiscoveryResponse(BaseModel):
    discovered: list[DiscoveredRepo]
    count: int
