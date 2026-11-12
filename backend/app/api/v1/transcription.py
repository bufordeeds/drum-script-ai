import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.models import STATUS_COMPLETED, TranscriptionJob
from app.queue import enqueue_transcription
from app.schemas.transcription import JobResponse, JobResultResponse

router = APIRouter()

# name in the URL -> (file on disk, media type, download extension)
RESULT_FILES = {
    "hits": ("hits.json", "application/json", ".hits.json"),
    "musicxml": ("score.musicxml", "application/vnd.recordare.musicxml+xml", ".musicxml"),
    "midi": ("score.mid", "audio/midi", ".mid"),
    "mix": ("mix.flac", "audio/flac", ".mix.flac"),
    "drums": ("drums.flac", "audio/flac", ".drums.flac"),
}


def job_dir(job_id: uuid.UUID) -> Path:
    return Path(settings.DATA_DIR) / "jobs" / str(job_id)


async def get_job_or_404(job_id: uuid.UUID, db: AsyncSession) -> TranscriptionJob:
    job = (await db.execute(select(TranscriptionJob).where(TranscriptionJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/upload", response_model=JobResponse, status_code=201)
async def upload_audio(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Store the upload, create a job row and queue the transcription."""
    name = Path(file.filename or "audio").name
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in settings.ALLOWED_AUDIO_FORMATS:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}")

    job_id = uuid.uuid4()
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"input.{ext}"
    size = 0
    try:
        with open(target, "wb") as out:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB)")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "Empty file")
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise

    job = TranscriptionJob(id=job_id, filename=name[:255], file_size_bytes=size)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    try:
        enqueue_transcription(str(job_id), str(target))
    except Exception as e:  # broker down
        job.status, job.error_message = "error", f"Could not queue job: {e}"
        await db.commit()
        raise HTTPException(503, "Job queue unavailable") from e
    return job


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(TranscriptionJob).order_by(TranscriptionJob.created_at.desc()).limit(min(limit, 100)))
    return rows.scalars().all()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await get_job_or_404(job_id, db)


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job_or_404(job_id, db)
    out = JobResultResponse(job_id=job.id, filename=job.filename, status=job.status)
    if job.status == STATUS_COMPLETED:
        out.summary = job.result
        out.files = {k: f"/api/v1/transcription/jobs/{job_id}/files/{k}" for k in RESULT_FILES}
    return out


@router.get("/jobs/{job_id}/files/{name}")
async def get_job_file(job_id: uuid.UUID, name: str, download: bool = False, db: AsyncSession = Depends(get_db)):
    """Serve one result file. `?download=1` adds a Content-Disposition with a friendly filename."""
    if name not in RESULT_FILES:
        raise HTTPException(404, "Unknown file")
    job = await get_job_or_404(job_id, db)
    if job.status != STATUS_COMPLETED:
        raise HTTPException(409, "Job is not finished")
    disk_name, media_type, ext = RESULT_FILES[name]
    path = job_dir(job_id) / disk_name
    if not path.exists():
        raise HTTPException(404, "File missing")
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(job.filename).stem).strip() or "drums"
    return FileResponse(path, media_type=media_type, filename=f"{stem}{ext}" if download else None)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job_or_404(job_id, db)
    await db.delete(job)
    await db.commit()
    shutil.rmtree(job_dir(job_id), ignore_errors=True)
