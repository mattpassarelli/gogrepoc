"""FastAPI application for GOGRepoc web interface.

This module provides the main FastAPI application with CORS middleware,
error handling, and logging configuration.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gogrepoc.core.exceptions import AuthError, FileSystemError, NetworkError

# Setup logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting GOGRepoc API server")
    yield
    # Shutdown
    logger.info("Shutting down GOGRepoc API server")


# Create FastAPI application
app = FastAPI(
    title="GOGRepoc API",
    description="REST API for GOG game repository management",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handling middleware
@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Handle authentication errors."""
    logger.warning(f"Authentication error: {exc}")
    return JSONResponse(
        status_code=401,
        content={"error": "Authentication failed", "detail": str(exc)},
    )


@app.exception_handler(NetworkError)
async def network_error_handler(request: Request, exc: NetworkError) -> JSONResponse:
    """Handle network errors."""
    logger.error(f"Network error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"error": "Network error", "detail": str(exc)},
    )


@app.exception_handler(FileSystemError)
async def filesystem_error_handler(request: Request, exc: FileSystemError) -> JSONResponse:
    """Handle file system errors."""
    logger.error(f"File system error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "File system error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"},
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Import routes after app is created to avoid circular imports
from gogrepoc.api import routes  # noqa: E402, F401

app.include_router(routes.router, prefix="/api")
