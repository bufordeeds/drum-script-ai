from celery import Celery
import structlog
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import datetime
import os

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.models.transcription import TranscriptionJob, JobStatus

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
        "app.tasks.transcription.process_audio_task": {"queue": "transcription"}
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50
)

logger = structlog.get_logger()


async def update_job_status(
    job_id: str,
    status: JobStatus,
    progress: int = None,
    error_message: str = None,
    result_data: dict = None
):
    """Update job status in database"""
    async with AsyncSessionLocal() as db:
        update_data = {"status": status}
        
        if progress is not None:
            update_data["progress"] = progress
        
        if error_message:
            update_data["error_message"] = error_message
        
        if result_data:
            update_data["result_data"] = result_data
        
        if status == JobStatus.PROCESSING and "started_at" not in update_data:
            update_data["started_at"] = datetime.utcnow()
        
        if status in [JobStatus.COMPLETED, JobStatus.ERROR]:
            update_data["completed_at"] = datetime.utcnow()
        
        await db.execute(
            update(TranscriptionJob)
            .where(TranscriptionJob.id == job_id)
            .values(**update_data)
        )
        await db.commit()


@celery_app.task(bind=True)
def process_audio_task(self, job_id: str, user_id: str, file_path: str):
    """Background task for audio processing"""
    logger.info(
        "Starting audio processing",
        job_id=job_id,
        user_id=user_id,
        file_path=file_path
    )
    
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Update status to processing
        loop.run_until_complete(
            update_job_status(job_id, JobStatus.PROCESSING, progress=10)
        )
        
        # TODO: Implement actual ML processing pipeline
        # For now, simulate processing with progress updates
        import time
        
        stages = [
            ("Validating audio file", 20),
            ("Separating drum track", 40),
            ("Transcribing drums", 70),
            ("Generating notation", 90),
            ("Finalizing results", 100)
        ]
        
        for stage_name, progress in stages:
            logger.info(f"Processing stage: {stage_name}", job_id=job_id, progress=progress)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'stage': stage_name, 'progress': progress}
            )
            
            loop.run_until_complete(
                update_job_status(job_id, JobStatus.PROCESSING, progress=progress)
            )
            
            # Simulate processing time
            time.sleep(2)
        
        # Mock result data
        result_data = {
            "tempo": 120,
            "time_signature": "4/4",
            "duration_seconds": 180.5,
            "accuracy_score": 0.85
        }
        
        # Mark as completed
        loop.run_until_complete(
            update_job_status(
                job_id,
                JobStatus.COMPLETED,
                progress=100,
                result_data=result_data
            )
        )
        
        logger.info("Audio processing completed", job_id=job_id)
        
        return {
            'status': 'completed',
            'result': result_data
        }
        
    except Exception as e:
        logger.error(
            "Audio processing failed",
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
                JobStatus.ERROR,
                error_message=str(e)
            )
        )
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        
        raise