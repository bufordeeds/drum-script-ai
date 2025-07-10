from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import uuid
import io

from app.core.database import get_db
from app.models import User, TranscriptionJob
# Job status constants
JOB_STATUS_COMPLETED = 'completed'
from app.config import settings

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
    
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    musicxml_data = job.result_data['exports'].get('musicxml')
    if not musicxml_data:
        raise HTTPException(status_code=404, detail="MusicXML export not found")
    
    # Convert bytes to file-like object
    if isinstance(musicxml_data, str):
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
    
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    midi_data = job.result_data['exports'].get('midi')
    if not midi_data:
        raise HTTPException(status_code=404, detail="MIDI export not found")
    
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
    
    if not job.result_data or 'exports' not in job.result_data:
        raise HTTPException(status_code=404, detail="Export data not found")
    
    pdf_data = job.result_data['exports'].get('pdf')
    if not pdf_data:
        raise HTTPException(status_code=404, detail="PDF export not found")
    
    # For the placeholder text PDF, convert to proper content type
    if isinstance(pdf_data, str):
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