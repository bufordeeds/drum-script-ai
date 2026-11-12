from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False
    ok = all(checks.values())
    return JSONResponse(status_code=200 if ok else 503, content={
        "status": "healthy" if ok else "unhealthy", "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(), "version": settings.VERSION})
