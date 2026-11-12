"""Celery client. The API only enqueues; the task itself lives in ml_worker/worker.py."""
from celery import Celery

from app.config import settings

TRANSCRIBE_TASK = "drumscript.transcribe"
TRANSCRIBE_QUEUE = "transcription"

celery_app = Celery("drumscript", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json",
                       broker_connection_retry_on_startup=True)


def enqueue_transcription(job_id: str, input_path: str) -> None:
    celery_app.send_task(TRANSCRIBE_TASK, args=[job_id, input_path], queue=TRANSCRIBE_QUEUE)
