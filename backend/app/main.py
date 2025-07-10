from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.api.v1 import transcription, health, export
from app.core.database import engine, Base


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Drum Transcription API")
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Drum Transcription API")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(transcription.router, prefix="/api/v1/transcription", tags=["transcription"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])


# WebSocket endpoint for real-time updates
@app.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    import redis.asyncio as aioredis
    import json
    import asyncio
    
    # Create Redis connection for pub/sub
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to job-specific progress channel
        await pubsub.subscribe(f"job_progress:{job_id}")
        
        # Send initial connection message
        await websocket.send_json({
            "job_id": job_id,
            "status": "connected",
            "message": "WebSocket connection established"
        })
        
        # Listen for progress updates and WebSocket messages
        async def listen_for_progress():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        progress_data = json.loads(message['data'])
                        await websocket.send_json(progress_data)
                    except Exception as e:
                        logger.error("Failed to send progress update", error=str(e))
        
        async def listen_for_websocket():
            while True:
                try:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
                except Exception:
                    break  # WebSocket closed
        
        # Run both listeners concurrently
        await asyncio.gather(
            listen_for_progress(),
            listen_for_websocket(),
            return_exceptions=True
        )
        
    except Exception as e:
        logger.error("WebSocket error", error=str(e), job_id=job_id)
    finally:
        await pubsub.unsubscribe(f"job_progress:{job_id}")
        await redis_client.close()
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)