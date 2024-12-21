"""
Main application module for the API service.

This module initializes and runs the FastAPI application with proper configuration,
middleware, and routers.
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.db import init_db, close_db

def setup_logging() -> logging.Logger:
    """Configure logging with proper formatting and level from settings."""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL.upper()}")

    return logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager for lifespan events (startup and shutdown).
    
    Args:
        app: FastAPI application instance
    """
    logger = logging.getLogger(__name__)
    
    # Startup
    logger.info("Starting up API service")
    try:
        await init_db()
        logger.info("Database initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down API service")
        try:
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sensor Monitoring API",
        description="API for managing sensor devices and readings",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Set up CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

# Create FastAPI application instance
app = create_application()
logger = setup_logging()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
