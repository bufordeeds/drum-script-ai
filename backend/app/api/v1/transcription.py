from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import os
import uuid
from datetime import datetime
import magic
import aiofiles

from app.core.database import get_db
from app.models import User, TranscriptionJob
from app.models.transcription import JobStatus as ModelJobStatus
from app.schemas.transcription import (
    FileUploadResponse, 
    JobStatusResponse, 
    JobResultResponse,
    JobStatus
)
from app.config import settings
from app.tasks.transcription import process_audio_task

router = APIRouter()
logger = structlog.get_logger()


# TODO: Replace with proper auth
async def get_current_user(db: AsyncSession) -> User:
    """Temporary user getter - replace with proper auth"""
    # For now, create or get a demo user
    result = await db.execute(
        select(User).where(User.email == "demo@example.com")
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(email="demo@example.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


def validate_audio_file(file: UploadFile) -> None:
    """Validate uploaded audio file"""
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Check file extension
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}"
        )
    
    # TODO: Add magic number validation for actual file type


@router.post("/upload", response_model=FileUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload audio file for transcription"""
    try:
        # Validate file
        validate_audio_file(file)
        
        # Create job record
        job = TranscriptionJob(
            user_id=current_user.id,
            filename=file.filename,
            file_size_bytes=file.size,
            status=ModelJobStatus.UPLOADING
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Save file to disk
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{job.id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Update job status
        job.status = ModelJobStatus.PENDING
        await db.commit()
        
        # Queue processing task
        process_audio_task.delay(
            str(job.id),
            str(current_user.id),
            file_path
        )
        
        logger.info(
            "File uploaded successfully",
            job_id=str(job.id),
            user_id=str(current_user.id),
            filename=file.filename
        )
        
        return FileUploadResponse(
            job_id=job.id,
            message="File uploaded successfully. Processing will begin shortly.",
            status=JobStatus.PENDING
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload failed", error=str(e))
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transcription job status"""
    # Query job
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Map status to schema
    status_map = {
        ModelJobStatus.PENDING: JobStatus.PENDING,
        ModelJobStatus.UPLOADING: JobStatus.UPLOADING,
        ModelJobStatus.VALIDATING: JobStatus.VALIDATING,
        ModelJobStatus.PROCESSING: JobStatus.PROCESSING,
        ModelJobStatus.COMPLETED: JobStatus.COMPLETED,
        ModelJobStatus.ERROR: JobStatus.ERROR
    }
    
    return JobStatusResponse(
        id=job.id,
        filename=job.filename,
        status=status_map[job.status],
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transcription job result"""
    # Query job with result
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != ModelJobStatus.COMPLETED:
        return JobResultResponse(
            job_id=job.id,
            status=JobStatus(job.status.value)
        )
    
    # TODO: Generate actual download URLs from S3
    download_urls = {
        "musicxml": f"/api/v1/export/musicxml/{job_id}",
        "midi": f"/api/v1/export/midi/{job_id}",
        "pdf": f"/api/v1/export/pdf/{job_id}"
    }
    
    return JobResultResponse(
        job_id=job.id,
        status=JobStatus.COMPLETED,
        result=job.result_data,
        download_urls=download_urls
    )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a transcription job"""
    # Query job
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # TODO: Clean up associated files in S3/local storage
    
    await db.delete(job)
    await db.commit()
    
    return {"message": "Job deleted successfully"}