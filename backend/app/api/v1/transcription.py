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
# Job status constants
JOB_STATUS_PENDING = 'pending'
JOB_STATUS_UPLOADING = 'uploading' 
JOB_STATUS_VALIDATING = 'validating'
JOB_STATUS_PROCESSING = 'processing'
JOB_STATUS_COMPLETED = 'completed'
JOB_STATUS_ERROR = 'error'
from app.schemas.transcription import (
    FileUploadResponse, 
    JobStatusResponse, 
    JobResultResponse,
    JobStatus
)
from app.config import settings
from app.tasks.transcription import celery_app
from app.services.s3 import s3_service

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
    db: AsyncSession = Depends(get_db)
):
    """Upload audio file for transcription"""
    try:
        # Validate file
        validate_audio_file(file)
        
        # Get current user
        current_user = await get_current_user(db)
        
        # Create job record
        job = TranscriptionJob(
            user_id=current_user.id,
            filename=file.filename,
            file_size_bytes=file.size,
            status=JOB_STATUS_UPLOADING
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Read file content
        content = await file.read()
        
        # Try S3 upload first, fallback to local storage
        s3_key = None
        file_path = None
        
        if s3_service.is_configured():
            try:
                # Generate S3 key for audio file
                s3_key = s3_service.generate_file_key(
                    prefix="audio",
                    filename=file.filename,
                    user_id=str(current_user.id)
                )
                
                # Upload to S3
                import io
                file_stream = io.BytesIO(content)
                s3_url = await s3_service.upload_file(
                    file_data=file_stream,
                    key=s3_key,
                    content_type=file.content_type,
                    metadata={
                        'user_id': str(current_user.id),
                        'job_id': str(job.id),
                        'original_filename': file.filename
                    }
                )
                
                if s3_url:
                    # Update job with S3 key
                    job.s3_audio_key = s3_key
                    logger.info("File uploaded to S3", job_id=str(job.id), s3_key=s3_key)
                else:
                    raise Exception("S3 upload returned None")
                    
            except Exception as e:
                logger.warning("S3 upload failed, falling back to local storage", 
                             error=str(e), job_id=str(job.id))
                s3_key = None
        
        # Fallback to local storage if S3 failed or not configured
        if not s3_key:
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(settings.UPLOAD_DIR, f"{job.id}_{file.filename}")
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.info("File saved locally", job_id=str(job.id), file_path=file_path)
        
        # Update job status
        job.status = JOB_STATUS_PENDING
        await db.commit()
        
        # Queue processing task with appropriate file reference
        file_reference = s3_key if s3_key else file_path
        celery_app.send_task(
            'app.tasks.transcription.process_audio_task',
            args=[str(job.id), str(current_user.id), file_reference],
            queue='backend'
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
    db: AsyncSession = Depends(get_db)
):
    """Get transcription job status"""
    # Get current user
    current_user = await get_current_user(db)
    
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
        JOB_STATUS_PENDING: JobStatus.PENDING,
        JOB_STATUS_UPLOADING: JobStatus.UPLOADING,
        JOB_STATUS_VALIDATING: JobStatus.VALIDATING,
        JOB_STATUS_PROCESSING: JobStatus.PROCESSING,
        JOB_STATUS_COMPLETED: JobStatus.COMPLETED,
        JOB_STATUS_ERROR: JobStatus.ERROR
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
    db: AsyncSession = Depends(get_db)
):
    """Get transcription job result"""
    # Get current user
    current_user = await get_current_user(db)
    
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
    
    if job.status != JOB_STATUS_COMPLETED:
        return JobResultResponse(
            job_id=job.id,
            status=JobStatus(job.status)
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
    db: AsyncSession = Depends(get_db)
):
    """Delete a transcription job"""
    # Get current user
    current_user = await get_current_user(db)
    
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