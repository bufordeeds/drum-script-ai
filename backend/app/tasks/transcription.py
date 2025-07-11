from celery import Celery
import structlog
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import datetime
import os
import redis
import json

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.models.transcription import TranscriptionJob

# Job status constants
JOB_STATUS_PROCESSING = 'processing'
JOB_STATUS_COMPLETED = 'completed' 
JOB_STATUS_ERROR = 'error'

# Initialize Celery
celery_app = Celery(
    "drum_transcription",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.transcription.process_audio_task": {"queue": "backend"}
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50
)

logger = structlog.get_logger()

# Redis client for pub/sub
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(job_id: str, status: str, progress: int, stage: str = None, message: str = None):
    """Publish progress update to Redis pub/sub channel"""
    try:
        progress_data = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "stage": stage,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to job-specific channel
        redis_client.publish(f"job_progress:{job_id}", json.dumps(progress_data))
        
        # Also publish to general progress channel
        redis_client.publish("job_progress", json.dumps(progress_data))
        
        logger.info("Published progress update", job_id=job_id, progress=progress, stage=stage)
        
    except Exception as e:
        logger.error("Failed to publish progress", job_id=job_id, error=str(e))


async def update_job_status(
    job_id: str,
    status: str,
    progress: int = None,
    error_message: str = None,
    result_data: dict = None,
    stage: str = None
):
    """Update job status in database and publish to WebSocket"""
    async with AsyncSessionLocal() as db:
        update_data = {"status": status}
        
        if progress is not None:
            update_data["progress"] = progress
        
        if error_message:
            update_data["error_message"] = error_message
        
        if result_data:
            update_data["result_data"] = result_data
        
        if status == JOB_STATUS_PROCESSING and "started_at" not in update_data:
            update_data["started_at"] = datetime.utcnow()
        
        if status in [JOB_STATUS_COMPLETED, JOB_STATUS_ERROR]:
            update_data["completed_at"] = datetime.utcnow()
        
        await db.execute(
            update(TranscriptionJob)
            .where(TranscriptionJob.id == job_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Publish progress update for real-time updates
        publish_progress(
            job_id=job_id,
            status=status,
            progress=progress or 0,
            stage=stage,
            message=error_message
        )


@celery_app.task(bind=True)
def process_audio_task(self, job_id: str, user_id: str, file_path: str):
    """Background task that delegates to ML worker for actual processing"""
    logger.info(
        "Delegating audio processing to ML worker",
        job_id=job_id,
        user_id=user_id,
        file_path=file_path
    )
    
    try:
        # Send task to ML worker
        from celery import Celery
        ml_worker = Celery(
            'drum_transcription_worker',
            broker=settings.CELERY_BROKER_URL,
            backend=settings.CELERY_RESULT_BACKEND
        )
        
        # Send to ML worker
        result = ml_worker.send_task(
            'tasks.transcription.transcribe_drums_task',
            args=[job_id, file_path],
            queue='transcription'
        )
        
        logger.info("Sent task to ML worker", job_id=job_id, task_id=result.id)
        return f"Delegated to ML worker with task ID: {result.id}"
        
    except Exception as e:
        logger.error(
            "Audio processing delegation failed",
            job_id=job_id,
            error=str(e),
            exc_info=True
        )
        
        # Update job with error
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            update_job_status(
                job_id,
                JOB_STATUS_ERROR,
                error_message=str(e),
                stage="error"
            )
        )
        
        raise