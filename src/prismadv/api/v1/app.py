"""PrismaDV Demo API - FastAPI Application."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from prismadv.api.v1 import dependencies
from prismadv.api.v1.dependencies import limiter
from prismadv.api.v1.routes import cached_runs, constraints, datasets, examples, files, optimization
from prismadv.api.v1.session import Session, SessionManager
from prismadv.api.v1.storage import StorageManager

logger = logging.getLogger(__name__)

# Configuration
SESSION_TTL_SECONDS = 3600  # 1 hour
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("🚀 PrismaDV API starting up...")

    # Initialize managers
    session_manager = SessionManager(ttl_seconds=SESSION_TTL_SECONDS)
    storage_manager = StorageManager()
    dependencies.init_managers(session_manager, storage_manager)

    logger.info(f"✓ Session TTL: {SESSION_TTL_SECONDS}s")
    logger.info(f"✓ Cleanup interval: {CLEANUP_INTERVAL_SECONDS}s")
    logger.info("✓ Managers initialized")

    # Pre-initialize Spark/Deequ in background to avoid cold-start delay
    def _preload_deequ():
        try:
            from prismadv.validation.deequ_validator import DeequValidator
            validator = DeequValidator()
            validator._get_or_create_spark()
            logger.info("✓ Deequ/Spark pre-initialized")
        except Exception as e:
            logger.warning(f"Deequ pre-initialization skipped: {e}")

    threading.Thread(target=_preload_deequ, daemon=True).start()

    yield

    # Shutdown
    logger.info("👋 PrismaDV API shutting down...")
    logger.info(f"  Active sessions: {session_manager.session_count()}")
    logger.info(f"  Active storages: {storage_manager.storage_count()}")


# Create FastAPI app
app = FastAPI(
    title="PrismaDV API",
    description="Backend API for PrismaDV constraint generation demo",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait before trying again."},
    )

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,  # Required for session cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(constraints.router, prefix="/api/v1")
app.include_router(examples.router, prefix="/api/v1")
app.include_router(optimization.router, prefix="/api/v1")
app.include_router(cached_runs.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "prismadv-api",
        "version": "1.0.0",
    }


@app.get("/api/v1/session/info")
async def get_session_info(session: Session = dependencies.Depends(dependencies.get_session)):
    """Get current session information.

    Args:
        session: Current session from dependency

    Returns:
        Session information
    """
    return {
        "sessionId": session.id,
        "createdAt": session.created_at,
        "lastAccessed": session.last_accessed,
    }


# Health endpoint with session stats (for debugging)
@app.get("/api/v1/stats")
async def get_stats(
    session_manager: SessionManager = dependencies.Depends(dependencies.get_session_manager),
    storage_manager: StorageManager = dependencies.Depends(dependencies.get_storage_manager),
):
    """Get API statistics.

    Args:
        session_manager: SessionManager instance
        storage_manager: StorageManager instance

    Returns:
        API statistics
    """
    return {
        "activeSessions": session_manager.session_count(),
        "activeStorages": storage_manager.storage_count(),
        "sessionTtl": SESSION_TTL_SECONDS,
    }
