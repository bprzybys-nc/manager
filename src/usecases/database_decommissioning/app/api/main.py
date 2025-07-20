"""
FastAPI Application for Database Decommissioning Use Case.

This module provides the main FastAPI application for the database decommissioning
use case, integrating with Manager's infrastructure while maintaining GraphMCP
framework compatibility.

Manager Integration:
- FastAPI application factory pattern
- Database client dependency injection
- Celery task integration
- Prometheus metrics
- Structured logging

GraphMCP Compatibility:
- WorkflowBuilder integration
- MCP client orchestration
- Async context management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from celery import Celery
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Manager imports
from src.database.client import DatabaseClient
from src.modules.task.db import TaskDB
import src.config as manager_config

# Local imports
from .routes import create_database_decommissioning_routes
from ..utils import create_logger_for_workflow, validate_environment_dependencies

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    
    Handles application startup and shutdown events for proper resource management.
    """
    # Startup
    logger.info("Starting Database Decommissioning API")
    
    # Validate environment on startup
    try:
        env_status = validate_environment_dependencies()
        if not env_status.get("overall_success"):
            logger.warning("Environment validation found issues", extra=env_status)
        else:
            logger.info("Environment validation passed")
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
    
    # Initialize monitoring if available
    try:
        # Add any startup monitoring here
        pass
    except Exception as e:
        logger.warning(f"Failed to initialize monitoring: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Database Decommissioning API")


def create_app(
    db_client: Optional[DatabaseClient] = None,
    task_db: Optional[TaskDB] = None,
    celery_app: Optional[Celery] = None,
    title: str = "Database Decommissioning API",
    version: str = "1.0.0",
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        db_client: Optional Manager database client
        task_db: Optional task database for integration
        celery_app: Optional Celery app for background tasks
        title: API title
        version: API version
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        version=version,
        description="AI-powered database decommissioning workflow automation",
        lifespan=lifespan,
    )
    
    # Add CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize database client if not provided
    if db_client is None:
        try:
            db_client = DatabaseClient({"uri": manager_config.MONGO_DB_URI})
        except Exception as e:
            logger.warning(f"Failed to initialize database client: {e}")
            db_client = None
    
    # Initialize task database if not provided
    if task_db is None and db_client is not None:
        try:
            task_db = TaskDB(db_client.client)
        except Exception as e:
            logger.warning(f"Failed to initialize task database: {e}")
            task_db = None
    
    # Initialize Celery app if not provided
    if celery_app is None:
        try:
            celery_app = Celery("database_decommissioning", broker=manager_config.CELERY_BROKER_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize Celery app: {e}")
            celery_app = None
    
    # Create routes
    if db_client is not None:
        routes = create_database_decommissioning_routes(
            db_client=db_client,
            task_db=task_db,
            celery_app=celery_app,
        )
        
        # Include routes
        app.include_router(routes.router, prefix="/api/v1")
        
        # Store references for dependency injection
        app.state.db_client = db_client
        app.state.task_db = task_db
        app.state.celery_app = celery_app
        app.state.routes = routes
    else:
        logger.error("Cannot create routes without database client")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "database_decommissioning"}
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "Database Decommissioning API",
            "version": version,
            "description": "AI-powered database decommissioning workflow automation",
            "endpoints": {
                "health": "/health",
                "api": "/api/v1",
                "docs": "/docs",
                "redoc": "/redoc",
            }
        }
    
    return app


# Dependency functions for FastAPI dependency injection
def get_db_client() -> DatabaseClient:
    """Get database client dependency."""
    try:
        return DatabaseClient({"uri": manager_config.MONGO_DB_URI})
    except Exception as e:
        logger.error(f"Failed to get database client: {e}")
        raise


def get_task_db(db_client: DatabaseClient = Depends(get_db_client)) -> Optional[TaskDB]:
    """Get task database dependency."""
    try:
        return TaskDB(db_client.client)
    except Exception as e:
        logger.warning(f"Failed to get task database: {e}")
        return None


def get_celery_app() -> Optional[Celery]:
    """Get Celery app dependency."""
    try:
        return Celery("database_decommissioning", broker=manager_config.CELERY_BROKER_URL)
    except Exception as e:
        logger.warning(f"Failed to get Celery app: {e}")
        return None


# Application factory for different environments
def create_development_app() -> FastAPI:
    """Create application configured for development."""
    return create_app(
        title="Database Decommissioning API (Development)",
        version="1.0.0-dev",
    )


def create_production_app() -> FastAPI:
    """Create application configured for production."""
    return create_app(
        title="Database Decommissioning API",
        version="1.0.0",
    )


# Default application instance
app = create_development_app()


if __name__ == "__main__":
    import uvicorn
    
    # Run development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )