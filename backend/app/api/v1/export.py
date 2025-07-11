from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import uuid
import io
import base64

from app.core.database import get_db
from app.models import User, TranscriptionJob
# Job status constants
JOB_STATUS_COMPLETED = 'completed'
from app.config import settings
from app.services.s3 import s3_service

router = APIRouter()
logger = structlog.get_logger()


# TODO: Replace with proper auth
async def get_current_user(db: AsyncSession) -> User:
    """Temporary user getter - replace with proper auth"""
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


async def get_completed_job(job_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> TranscriptionJob:
    """Get a completed transcription job"""
    result = await db.execute(
        select(TranscriptionJob).where(
            TranscriptionJob.id == job_id,
            TranscriptionJob.user_id == user_id,
            TranscriptionJob.status == JOB_STATUS_COMPLETED
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Completed job not found")
    
    return job


@router.get("/musicxml/{job_id}")
async def download_musicxml(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download MusicXML file"""
    current_user = await get_current_user(db)
    job = await get_completed_job(job_id, current_user.id, db)
    
    # Check if file is stored in S3
    if job.s3_export_keys and 'musicxml' in job.s3_export_keys:
        # Generate presigned URL for direct S3 access
        s3_key = job.s3_export_keys['musicxml']
        presigned_url = await s3_service.generate_presigned_url(s3_key, expiration=3600)
        
        if presigned_url:
            # Redirect to presigned URL for efficient download
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url)
        else:
            # Fallback: stream from S3
            file_stream = await s3_service.get_file_stream(s3_key)
            if file_stream:
                return StreamingResponse(
                    file_stream,
                    media_type="application/vnd.recordare.musicxml+xml",
                    headers={"Content-Disposition": f"attachment; filename={job.filename}.musicxml"}
                )
    
    # Fallback to result_data (base64 encoded)
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    musicxml_data = job.result_data['exports'].get('musicxml')
    if not musicxml_data:
        raise HTTPException(status_code=404, detail="MusicXML export not found")
    
    # Decode base64 data back to bytes
    if isinstance(musicxml_data, str):
        try:
            musicxml_data = base64.b64decode(musicxml_data)
        except Exception:
            # Fallback for non-base64 string data
            musicxml_data = musicxml_data.encode('utf-8')
    
    return StreamingResponse(
        io.BytesIO(musicxml_data),
        media_type="application/vnd.recordare.musicxml+xml",
        headers={"Content-Disposition": f"attachment; filename={job.filename}.musicxml"}
    )


@router.get("/midi/{job_id}")
async def download_midi(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download MIDI file"""
    current_user = await get_current_user(db)
    job = await get_completed_job(job_id, current_user.id, db)
    
    # Check if file is stored in S3
    if job.s3_export_keys and 'midi' in job.s3_export_keys:
        # Generate presigned URL for direct S3 access
        s3_key = job.s3_export_keys['midi']
        presigned_url = await s3_service.generate_presigned_url(s3_key, expiration=3600)
        
        if presigned_url:
            # Redirect to presigned URL for efficient download
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url)
        else:
            # Fallback: stream from S3
            file_stream = await s3_service.get_file_stream(s3_key)
            if file_stream:
                return StreamingResponse(
                    file_stream,
                    media_type="audio/midi",
                    headers={"Content-Disposition": f"attachment; filename={job.filename}.mid"}
                )
    
    # Fallback to result_data (base64 encoded)
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    midi_data = job.result_data['exports'].get('midi')
    if not midi_data:
        raise HTTPException(status_code=404, detail="MIDI export not found")
    
    # Decode base64 data back to bytes
    if isinstance(midi_data, str):
        try:
            midi_data = base64.b64decode(midi_data)
        except Exception:
            raise HTTPException(status_code=500, detail="Invalid MIDI data format")
    
    return StreamingResponse(
        io.BytesIO(midi_data),
        media_type="audio/midi",
        headers={"Content-Disposition": f"attachment; filename={job.filename}.mid"}
    )


@router.get("/pdf/{job_id}")
async def download_pdf(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download PDF file"""
    current_user = await get_current_user(db)
    job = await get_completed_job(job_id, current_user.id, db)
    
    # Check if file is stored in S3
    if job.s3_export_keys and 'pdf' in job.s3_export_keys:
        # Generate presigned URL for direct S3 access
        s3_key = job.s3_export_keys['pdf']
        presigned_url = await s3_service.generate_presigned_url(s3_key, expiration=3600)
        
        if presigned_url:
            # Redirect to presigned URL for efficient download
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url)
        else:
            # Fallback: stream from S3
            file_stream = await s3_service.get_file_stream(s3_key)
            if file_stream:
                return StreamingResponse(
                    file_stream,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={job.filename}.pdf"}
                )
    
    # Fallback to result_data (base64 encoded)
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    pdf_data = job.result_data['exports'].get('pdf')
    if not pdf_data:
        raise HTTPException(status_code=404, detail="PDF export not found")
    
    # Decode base64 data back to bytes
    if isinstance(pdf_data, str):
        try:
            # Try to decode as base64 first
            pdf_data = base64.b64decode(pdf_data)
            media_type = "application/pdf"
            filename = f"{job.filename}.pdf"
        except Exception:
            # Fallback for text data (placeholder)
            pdf_data = pdf_data.encode('utf-8')
            media_type = "text/plain"
            filename = f"{job.filename}.txt"
    else:
        media_type = "application/pdf"
        filename = f"{job.filename}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_data),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )