from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import redis.asyncio as redis
import structlog

from app.core.database import get_db
from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


async def check_database_connection(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


async def check_redis_connection() -> bool:
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        return True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check endpoint"""
    checks = {
        "database": await check_database_connection(db),
        "redis": await check_redis_connection(),
        "file_storage": True,  # TODO: Implement S3 check for production
        "ml_models": True      # TODO: Check model availability
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION
        }
    )