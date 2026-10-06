"""
Main FastAPI application for Fluxion backend
"""

import logging
import time
from contextlib import asynccontextmanager

from api.v1.router import api_router
from config.database import close_database, init_database
from config.settings import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from middleware.rate_limit_middleware import RateLimitMiddleware
from middleware.security_middleware import SecurityMiddleware
from schemas.base import ErrorResponse, ValidationErrorResponse
from services.ml import get_ml_gateway
from starlette.exceptions import HTTPException as StarletteHTTPException

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.app.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application startup time
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Fluxion backend application...")

    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")

        try:
            await get_ml_gateway().startup()
        except Exception as ml_exc:
            logger.error(f"ML gateway failed to start: {str(ml_exc)}")

        # Additional startup tasks can be added here
        # - Initialize Redis connection
        # - Start background tasks
        # - Load ML models
        # - Initialize blockchain connections

        logger.info("Application startup completed")

    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Fluxion backend application...")

    try:
        await get_ml_gateway().shutdown()
        await close_database()
        logger.info("Database connections closed")

        # Additional cleanup tasks can be added here
        # - Close Redis connections
        # - Stop background tasks
        # - Clean up resources

        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Application shutdown error: {str(e)}")


import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class _CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


from starlette.responses import JSONResponse as _StarletteJSONResponse


class _PatchedJSONResponse(_StarletteJSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=_CustomEncoder,
        ).encode("utf-8")


import fastapi.responses as _fr
import starlette.responses as _sr

_sr.JSONResponse = _PatchedJSONResponse
_fr.JSONResponse = _PatchedJSONResponse


# Create FastAPI application
app = FastAPI(
    title=settings.app.APP_NAME,
    description="Production-ready DeFi supply chain platform backend with enterprise-grade security and compliance",
    version=settings.app.VERSION,
    docs_url="/docs" if settings.app.DEBUG else None,
    redoc_url="/redoc" if settings.app.DEBUG else None,
    openapi_url="/openapi.json" if settings.app.DEBUG else None,
    lifespan=lifespan,
)

import fastapi.responses as _fastapi_responses

# Patch FastAPI's default JSON encoder to handle datetime/Decimal/UUID

_fastapi_responses.JSONResponse.media_type = "application/json"

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
)

# Add trusted host middleware
if settings.app.ALLOWED_HOSTS and settings.app.ALLOWED_HOSTS not in ("*", ["*"]):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.app.ALLOWED_HOSTS)


# Exception handlers


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail, error_code=f"HTTP_{exc.status_code}"
        ).model_dump(mode="json"),
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
):
    """Handle Starlette HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail, error_code=f"HTTP_{exc.status_code}"
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    validation_errors = []
    for error in exc.errors():
        validation_errors.append(
            {
                "field": " -> ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            validation_errors=validation_errors,
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    if settings.app.DEBUG:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=str(exc),
                error_code="INTERNAL_SERVER_ERROR",
                details={"type": type(exc).__name__},
            ).model_dump(mode="json"),
        )
    else:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error", error_code="INTERNAL_SERVER_ERROR"
            ).model_dump(mode="json"),
        )


# Middleware for request logging and timing
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log requests and measure response time"""
    start_time = time.time()

    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}"
    )

    # Process request
    response = await call_next(request)

    # Calculate response time
    process_time = time.time() - start_time

    # Add response headers
    response.headers["X-Process-Time"] = str(process_time)

    # Log response
    logger.info(
        f"Response: {response.status_code} for {request.method} {request.url.path} "
        f"in {process_time:.4f}s"
    )

    return response


# Health check endpoints
@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app.VERSION,
        "uptime": time.time() - app_start_time,
    }


async def _ml_health():
    try:
        status = await get_ml_gateway().status()
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}
    return {
        "status": "healthy" if status.get("ready") else "degraded",
        "mode": status.get("mode"),
        "missing": status.get("missing", []),
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with service status"""
    from config.database import DatabaseHealthCheck

    # Check database health
    db_write_health = await DatabaseHealthCheck.check_write_db()
    db_read_health = await DatabaseHealthCheck.check_read_db()

    # Overall health status
    overall_status = "healthy"
    if db_write_health.get("status") != "healthy" or (
        db_read_health.get("status") not in ["healthy", "not_configured"]
    ):
        overall_status = "unhealthy"

    ml_health = await _ml_health()

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "version": settings.app.VERSION,
        "uptime": time.time() - app_start_time,
        "services": {
            "database_write": db_write_health,
            "database_read": db_read_health,
            "ml": ml_health,
            # Add other service checks here
            # "redis": redis_health,
            # "blockchain": blockchain_health,
        },
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Application metrics endpoint"""
    return {
        "timestamp": time.time(),
        "uptime": time.time() - app_start_time,
        "version": settings.app.VERSION,
        "environment": settings.app.ENVIRONMENT,
        # Add more metrics here
        "memory_usage": "N/A",  # Would implement actual memory monitoring
        "cpu_usage": "N/A",  # Would implement actual CPU monitoring
        "request_count": "N/A",  # Would implement request counting
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Fluxion DeFi Supply Chain Platform API",
        "version": settings.app.VERSION,
        "environment": settings.app.ENVIRONMENT,
        "docs_url": "/docs" if settings.app.DEBUG else None,
        "health_url": "/health",
        "api_url": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.DEBUG,
        log_level=settings.app.LOG_LEVEL.lower(),
        access_log=True,
    )
