from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

JobStatus = Literal["pending", "processing", "completed", "error"]


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: JobStatus
    stage: Optional[str] = None
    progress: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobResultResponse(BaseModel):
    job_id: UUID
    filename: str
    status: JobStatus
    summary: Optional[dict] = None
    files: Optional[dict[str, str]] = None
