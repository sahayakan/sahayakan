from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: int
    run_id: int
    artifact_type: str
    storage_uri: str
    metadata: dict[str, Any] | None
    created_at: datetime
