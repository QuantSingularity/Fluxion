"""
Health check routes for Fluxion Backend
"""

import time
from typing import Any, Dict

from config.database import DatabaseHealthCheck
from config.settings import settings
from fastapi import APIRouter
from services.ml import get_ml_gateway

router = APIRouter()

_start_time = time.time()


@router.get("/", summary="Basic health check")
async def health() -> Dict[str, Any]:
    """Returns basic service health status."""
    return {
        "status": "healthy",
        "version": settings.app.VERSION,
        "environment": settings.app.ENVIRONMENT,
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@router.get("/detailed", summary="Detailed health check")
async def health_detailed() -> Dict[str, Any]:
    """Returns detailed health including all dependencies."""
    db_write = await DatabaseHealthCheck.check_write_db()
    db_read = await DatabaseHealthCheck.check_read_db()

    overall = "healthy"
    if db_write.get("status") != "healthy":
        overall = "degraded"
    if db_read.get("status") not in ("healthy", "not_configured"):
        overall = "degraded"

    try:
        ml_status = await get_ml_gateway().status()
        ml = {
            "status": "healthy" if ml_status.get("ready") else "degraded",
            "mode": ml_status.get("mode"),
            "missing": ml_status.get("missing", []),
        }
    except Exception as exc:
        ml = {"status": "unavailable", "error": str(exc)}

    return {
        "status": overall,
        "version": settings.app.VERSION,
        "environment": settings.app.ENVIRONMENT,
        "uptime_seconds": round(time.time() - _start_time, 2),
        "dependencies": {
            "database_primary": db_write,
            "database_replica": db_read,
            "ml": ml,
        },
    }


@router.get("/ready", summary="Readiness probe")
async def readiness() -> Dict[str, Any]:
    """Kubernetes-style readiness probe."""
    db_health = await DatabaseHealthCheck.check_write_db()
    if db_health.get("status") != "healthy":
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@router.get("/live", summary="Liveness probe")
async def liveness() -> Dict[str, Any]:
    """Kubernetes-style liveness probe."""
    return {"status": "alive", "uptime_seconds": round(time.time() - _start_time, 2)}
