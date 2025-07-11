import os
import json
import tempfile
import base64
from datetime import datetime
from typing import Dict, Any
import redis
import structlog
import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine, text
from worker import celery_app
from pipeline.transcription import TranscriptionPipeline

logger = structlog.get_logger()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/drum_transcription')
engine = create_engine(DATABASE_URL)

# Redis connection for progress updates
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

# S3 configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Initialize S3 client if credentials are available
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET:
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        logger.info("S3 client initialized for ML worker")
    except Exception as e:
        logger.warning("Failed to initialize S3 client", error=str(e))
        s3_client = None
else:
    logger.info("S3 credentials not configured, using local file access only")

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

def convert_bytes_to_base64(data):
    """Recursively convert bytes objects to base64 strings for JSON serialization"""
    if isinstance(data, bytes):
        return base64.b64encode(data).decode('utf-8')
    elif isinstance(data, dict):
        return {key: convert_bytes_to_base64(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_bytes_to_base64(item) for item in data]
    else:
        return data

def download_file_from_s3_or_local(file_reference: str) -> str:
    """Download file from S3 or return local path"""
    if file_reference.startswith('audio/'):  # S3 key format
        if not s3_client:
            raise ValueError("S3 client not available but S3 key provided")
        
        # Create temporary file for S3 download
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            logger.info("Downloading file from S3", s3_key=file_reference)
            s3_client.download_file(AWS_S3_BUCKET, file_reference, temp_path)
            logger.info("File downloaded from S3", local_path=temp_path)
            return temp_path
        except ClientError as e:
            logger.error("Failed to download from S3", error=str(e), s3_key=file_reference)
            raise
    else:
        # Local file path
        if not os.path.exists(file_reference):
            raise FileNotFoundError(f"Local file not found: {file_reference}")
        logger.info("Using local file", file_path=file_reference)
        return file_reference

def upload_export_to_s3(export_data: bytes, export_type: str, job_id: str) -> str:
    """Upload export file to S3 and return the key"""
    if not s3_client:
        return None
    
    try:
        # Generate S3 key for export
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"exports/{job_id}/{timestamp}_{export_type}"
        
        # Determine content type
        content_types = {
            'musicxml': 'application/vnd.recordare.musicxml+xml',
            'midi': 'audio/midi',
            'pdf': 'application/pdf'
        }
        content_type = content_types.get(export_type, 'application/octet-stream')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key,
            Body=export_data,
            ContentType=content_type,
            ServerSideEncryption='AES256',
            Metadata={
                'job_id': job_id,
                'export_type': export_type,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info("Export uploaded to S3", s3_key=s3_key, export_type=export_type)
        return s3_key
    except Exception as e:
        logger.error("Failed to upload export to S3", error=str(e), export_type=export_type)
        return None

def update_job_in_db(job_id: str, status: str, progress: int = None, 
                     error_message: str = None, result_data: Dict[str, Any] = None):
    """Update job status in database"""
    with engine.connect() as conn:
        query_parts = ["UPDATE transcription_jobs SET status = :status"]
        params = {"job_id": job_id, "status": status}
        
        if progress is not None:
            query_parts.append("progress = :progress")
            params["progress"] = progress
            
            
        if error_message is not None:
            query_parts.append("error_message = :error_message")
            params["error_message"] = error_message
            
        if result_data is not None:
            query_parts.append("result_data = :result_data")
            # Convert bytes to base64 before JSON serialization
            serializable_data = convert_bytes_to_base64(result_data)
            params["result_data"] = json.dumps(serializable_data)
            
        if status == 'completed':
            query_parts.append("completed_at = NOW()")
        elif status == 'processing':
            query_parts.append("started_at = NOW()")
            
        query = ", ".join(query_parts) + " WHERE id = :job_id"
        conn.execute(text(query), params)
        conn.commit()

@celery_app.task(bind=True)
def transcribe_drums_task(self, job_id: str, file_reference: str):
    """
    Main task for drum transcription processing
    """
    logger.info("Starting drum transcription", job_id=job_id, file_reference=file_reference)
    
    local_file_path = None
    temp_file_downloaded = False
    
    try:
        # Download file from S3 or get local path
        local_file_path = download_file_from_s3_or_local(file_reference)
        temp_file_downloaded = file_reference.startswith('audio/')  # Track if we downloaded from S3
        
        # Initialize pipeline
        pipeline = TranscriptionPipeline()
        
        # Update job status to processing
        update_job_in_db(job_id, 'processing', 0)
        publish_progress(job_id, 'processing', 0, 'validating')
        
        # Use the existing process_audio method which handles all steps
        from pipeline.transcription import ProcessingJob
        processing_job = ProcessingJob(
            job_id=job_id,
            audio_file_path=local_file_path,
            user_id="system",  # No user context in worker
            settings={}
        )
        
        # Run async method in sync context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        final_result = loop.run_until_complete(pipeline.process_audio(processing_job))
        
        # Upload exports to S3 if configured and update result data
        s3_export_keys = {}
        if s3_client and 'exports' in final_result:
            for export_type, export_data in final_result['exports'].items():
                if isinstance(export_data, bytes):
                    s3_key = upload_export_to_s3(export_data, export_type, job_id)
                    if s3_key:
                        s3_export_keys[export_type] = s3_key
        
        # Update database with S3 export keys if available
        if s3_export_keys:
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE transcription_jobs SET s3_export_keys = :s3_keys WHERE id = :job_id"),
                    {"s3_keys": json.dumps(s3_export_keys), "job_id": job_id}
                )
                conn.commit()
            logger.info("S3 export keys saved", job_id=job_id, keys=s3_export_keys)
        
        # Complete the job
        update_job_in_db(job_id, 'completed', 100, result_data=final_result)
        publish_progress(job_id, 'completed', 100, 'completed')
        
        logger.info("Transcription completed successfully", job_id=job_id)
        return final_result
        
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        logger.error("Transcription failed", job_id=job_id, error=str(e), exc_info=True)
        
        update_job_in_db(job_id, 'error', error_message=error_msg)
        publish_progress(job_id, 'error', 0)
        
        raise self.retry(exc=e, countdown=60, max_retries=3)
    
    finally:
        # Clean up temporary file if we downloaded from S3
        if temp_file_downloaded and local_file_path and os.path.exists(local_file_path):
            try:
                os.unlink(local_file_path)
                logger.info("Cleaned up temporary file", file_path=local_file_path)
            except Exception as e:
                logger.warning("Failed to clean up temporary file", error=str(e), file_path=local_file_path)