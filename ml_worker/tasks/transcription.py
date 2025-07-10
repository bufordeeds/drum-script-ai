import os
import json
import tempfile
from datetime import datetime
from typing import Dict, Any
import redis
import structlog
from sqlalchemy import create_engine, text
from worker import celery_app
from pipeline.transcription import TranscriptionPipeline

logger = structlog.get_logger()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/drum_transcription')
engine = create_engine(DATABASE_URL)

# Redis connection for progress updates
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

def publish_progress(job_id: str, status: str, progress: int, stage: str = None):
    """Publish job progress to Redis"""
    progress_data = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "stage": stage,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish(f"job_progress:{job_id}", json.dumps(progress_data))
    logger.info("Published progress", job_id=job_id, status=status, progress=progress, stage=stage)

def update_job_in_db(job_id: str, status: str, progress: int = None, stage: str = None, 
                     error_message: str = None, result_data: Dict[str, Any] = None):
    """Update job status in database"""
    with engine.connect() as conn:
        query_parts = ["UPDATE transcription_jobs SET status = :status"]
        params = {"job_id": job_id, "status": status}
        
        if progress is not None:
            query_parts.append("progress = :progress")
            params["progress"] = progress
            
        if stage is not None:
            query_parts.append("stage = :stage")
            params["stage"] = stage
            
        if error_message is not None:
            query_parts.append("error_message = :error_message")
            params["error_message"] = error_message
            
        if result_data is not None:
            query_parts.append("result_data = :result_data")
            params["result_data"] = json.dumps(result_data)
            
        if status == 'completed':
            query_parts.append("completed_at = NOW()")
        elif status == 'processing' and stage == 'validating':
            query_parts.append("started_at = NOW()")
            
        query = " ".join(query_parts) + " WHERE id = :job_id"
        conn.execute(text(query), params)
        conn.commit()

@celery_app.task(bind=True)
def transcribe_drums_task(self, job_id: str, file_path: str):
    """
    Main task for drum transcription processing
    """
    logger.info("Starting drum transcription", job_id=job_id, file_path=file_path)
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline()
        
        # Update job status to processing
        update_job_in_db(job_id, 'processing', 0, 'validating')
        publish_progress(job_id, 'processing', 0, 'validating')
        
        # Use the existing process_audio method which handles all steps
        from pipeline.transcription import ProcessingJob
        processing_job = ProcessingJob(
            job_id=job_id,
            audio_file_path=file_path,
            user_id="system",  # No user context in worker
            settings={}
        )
        
        # Run async method in sync context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        final_result = loop.run_until_complete(pipeline.process_audio(processing_job))
        
        # Step 7: Complete (100%)
        update_job_in_db(job_id, 'completed', 100, 'completed', result_data=final_result)
        publish_progress(job_id, 'completed', 100, 'completed')
        
        logger.info("Transcription completed successfully", job_id=job_id)
        return final_result
        
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        logger.error("Transcription failed", job_id=job_id, error=str(e), exc_info=True)
        
        update_job_in_db(job_id, 'error', error_message=error_msg)
        publish_progress(job_id, 'error', 0)
        
        raise self.retry(exc=e, countdown=60, max_retries=3)