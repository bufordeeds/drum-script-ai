"""Celery worker: runs the drumscript pipeline for one job and reports progress.

Progress goes to Postgres (polled by the API) and to a Redis pub/sub channel
(`job_progress:<id>`, forwarded by the API's websocket).
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from pathlib import Path

import redis
from celery import Celery
from celery.signals import worker_ready
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("drumscript.worker")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://drumuser:drumpass@postgres:5432/drumtranscribe")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("drumscript",
                    broker=os.getenv("CELERY_BROKER_URL", REDIS_URL),
                    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL))
celery_app.conf.update(
    task_serializer="json", accept_content=["json"], result_serializer="json",
    task_default_queue="transcription", worker_prefetch_multiplier=1, task_acks_late=False,
    broker_connection_retry_on_startup=True,
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
redis_client = redis.from_url(REDIS_URL)


def update_job(job_id: str, **fields) -> None:
    """UPDATE transcription_jobs SET <fields>; also publish the change on Redis."""
    sets, params = [], {"id": job_id}
    for key, value in fields.items():
        if key == "result":
            sets.append("result = CAST(:result AS JSONB)")
            params["result"] = json.dumps(value)
        elif key in ("started_at", "completed_at"):
            sets.append(f"{key} = NOW()")
        else:
            sets.append(f"{key} = :{key}")
            params[key] = value
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE transcription_jobs SET {', '.join(sets)} WHERE id = :id"), params)
    try:
        event = {"job_id": job_id, **{k: v for k, v in fields.items() if k in ("status", "stage", "progress", "error_message")}}
        redis_client.publish(f"job_progress:{job_id}", json.dumps(event))
    except Exception:  # pub/sub is best effort
        pass


@celery_app.task(name="drumscript.transcribe")
def transcribe(job_id: str, input_path: str) -> dict:
    from drumscript.audio import AudioError
    from drumscript.pipeline import run

    log.info("Job %s: %s", job_id, input_path)
    update_job(job_id, status="processing", stage="queued", progress=1, started_at=True)
    with engine.connect() as conn:
        filename = conn.execute(text("SELECT filename FROM transcription_jobs WHERE id = :id"), {"id": job_id}).scalar()
    title = Path(filename).stem if filename else None

    def progress(stage: str, pct: int) -> None:
        if stage != "done":
            update_job(job_id, stage=stage, progress=pct)

    try:
        doc = run(input_path, Path(input_path).parent, progress=progress, title=title)
    except AudioError as e:
        update_job(job_id, status="error", error_message=str(e), completed_at=True)
        return {"status": "error", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        log.exception("Job %s failed", job_id)
        update_job(job_id, status="error", error_message=f"Transcription failed: {type(e).__name__}: {e}"[:1000],
                   completed_at=True)
        return {"status": "error", "error": str(e)}

    summary = {
        "duration_s": doc["source"]["duration_s"],
        "tempo_bpm": doc["tempo_bpm"],
        "time_signature": doc["time_signature"],
        "bars": len(doc["bars"]),
        "hits": len(doc["hits"]),
        "hits_per_drum": dict(Counter(h["drum"] for h in doc["hits"])),
        "models": doc["models"],
        "timings_s": doc.get("timings_s"),
    }
    update_job(job_id, status="completed", stage="done", progress=100, result=summary, completed_at=True)
    return {"status": "completed", **summary}


@worker_ready.connect
def preload_models(**_):
    """Download/load model weights at startup so the first job is not slowed by it."""
    if os.getenv("DRUMSCRIPT_PRELOAD", "1") != "1":
        return
    try:
        from drumscript import beats, separate, transcribe as tr
        import numpy as np

        silence = np.zeros((2, 44100 * 2), dtype=np.float32)
        separate._get_model()
        tr.detect_hits(silence, 44100)      # also warms librosa/numba, which is slow on first use
        beats.track_beats(silence, 44100)
        log.info("Models loaded")
    except Exception:  # noqa: BLE001
        log.exception("Model preload failed (will retry on first job)")
