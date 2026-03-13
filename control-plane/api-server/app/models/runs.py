from datetime import datetime

from pydantic import BaseModel


class RunResponse(BaseModel):
    id: int
    job_id: int
    agent_name: str
    status: str
    start_time: datetime
    end_time: datetime | None
    git_commit: str | None
    logs_uri: str | None
