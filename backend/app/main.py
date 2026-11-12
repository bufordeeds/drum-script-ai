import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables)
from app.api.v1 import health, transcription
from app.config import settings
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("drumscript.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Postgres may still be starting when the container comes up.
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 29:
                raise
            logger.info("Waiting for database (%s)", type(e).__name__)
            await asyncio.sleep(2)
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.BACKEND_CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(transcription.router, prefix="/api/v1/transcription", tags=["transcription"])


@app.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    """Push progress events published by the worker on Redis (optional; the UI also polls)."""
    import redis.asyncio as aioredis

    await websocket.accept()
    client = aioredis.from_url(settings.REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(f"job_progress:{job_id}")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_json(json.loads(message["data"]))
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await pubsub.unsubscribe()
        await client.aclose()
