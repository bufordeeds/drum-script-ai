from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ProcessingStage(str, Enum):
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PREPROCESSING = "preprocessing"
    SOURCE_SEPARATION = "source_separation"
    TRANSCRIBING = "transcribing"
    POST_PROCESSING = "post_processing"
    GENERATING_EXPORTS = "generating_exports"
    COMPLETED = "completed"


class FileUploadResponse(BaseModel):
    job_id: UUID
    message: str
    status: JobStatus
    
    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    stage: Optional[ProcessingStage] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TranscriptionResult(BaseModel):
    tempo: int
    time_signature: str
    duration_seconds: float
    accuracy_score: float = Field(ge=0, le=1)
    
    model_config = ConfigDict(from_attributes=True)


class JobResultResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    result: Optional[TranscriptionResult] = None
    download_urls: Optional[dict[str, str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProgressUpdate(BaseModel):
    job_id: UUID
    status: JobStatus
    progress: int
    stage: ProcessingStage
    message: Optional[str] = None