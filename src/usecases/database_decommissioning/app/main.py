"""
Database Decommissioning Use Case - Main FastAPI Application.

This module provides the main FastAPI application for the database decommissioning
use case with Manager integration and GraphMCP framework compatibility.

Manager Integration:
- Standard Manager application patterns
- Database client integration
- Celery task integration
- Standard middleware and error handling

GraphMCP Preservation:
- Full GraphMCP workflow orchestration compatibility
- MCP client integration and configuration
- Workflow builder patterns and execution
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from celery import Celery
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Manager imports
import src.config as manager_config
from src.database.client import DatabaseClient
from src.modules.task.db import TaskDB

# Local imports
from .api import get_database_decommissioning_router
from .models import ErrorResponse
from .utils import create_logger_for_workflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Database Decommissioning service")
    
    # Initialize database client
    try:
        db_client = DatabaseClient({"uri": manager_config.MONGO_DB_URI})
        app.state.db_client = db_client
        logger.info("Database client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database client: {e}")
        raise

    # Initialize optional Celery app
    try:
        celery_app = Celery("database_decommissioning", broker=manager_config.CELERY_BROKER_URL)
        app.state.celery_app = celery_app
        logger.info("Celery integration initialized")
    except Exception as e:
        logger.warning(f"Celery integration not available: {e}")
        app.state.celery_app = None

    # Initialize optional TaskDB
    try:
        if hasattr(app.state, 'db_client'):
            task_db = TaskDB(app.state.db_client.client)
            app.state.task_db = task_db
            logger.info("Task database initialized")
    except Exception as e:
        logger.warning(f"Task database not available: {e}")
        app.state.task_db = None

    yield
    
    # Cleanup
    logger.info("Shutting down Database Decommissioning service")
    if hasattr(app.state, 'db_client'):
        try:
            await app.state.db_client.close()
            logger.info("Database client closed")
        except Exception as e:
            logger.error(f"Error closing database client: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Database Decommissioning Service",
        description="AI-powered database decommissioning workflow service with Manager integration",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal Server Error",
                message=str(exc),
                details={"request_url": str(request.url)},
            ).dict()
        )

    # HTTP exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=f"HTTP {exc.status_code}",
                message=exc.detail,
                details={"request_url": str(request.url)},
            ).dict()
        )

    return app


def setup_routes(app: FastAPI):
    """
    Setup API routes for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Include database decommissioning routes
    @app.on_event("startup")
    async def setup_database_routes():
        """Setup routes after application startup."""
        try:
            # Get router with dependency injection
            router = await get_database_decommissioning_router(
                db_client=app.state.db_client,
                task_db=getattr(app.state, 'task_db', None),
                celery_app=getattr(app.state, 'celery_app', None),
            )
            
            # Include router with prefix
            app.include_router(router, prefix="/api/v1/database-decommissioning", tags=["Database Decommissioning"])
            
            logger.info("Database decommissioning routes configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup routes: {e}")
            raise

    # Root endpoint
    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "Database Decommissioning",
            "version": "1.0.0",
            "description": "AI-powered database decommissioning workflow service",
            "manager_integration": True,
            "graphmcp_compatibility": True,
            "docs_url": "/docs",
            "health_url": "/api/v1/database-decommissioning/health",
        }

    # Service health endpoint
    @app.get("/health", tags=["Health"])
    async def health():
        """Basic health check endpoint."""
        try:
            # Check database connectivity
            if hasattr(app.state, 'db_client'):
                await app.state.db_client.database.command("ping")
                db_status = "healthy"
            else:
                db_status = "unavailable"

            return {
                "status": "healthy",
                "service": "database_decommissioning",
                "version": "1.0.0",
                "components": {
                    "database": db_status,
                    "celery": "available" if hasattr(app.state, 'celery_app') and app.state.celery_app else "unavailable",
                    "task_db": "available" if hasattr(app.state, 'task_db') and app.state.task_db else "unavailable",
                },
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "service": "database_decommissioning",
                    "version": "1.0.0",
                }
            )


# Create the application instance
app = create_app()
setup_routes(app)


# Manager integration helpers
def get_database_decommissioning_app() -> FastAPI:
    """
    Get the database decommissioning FastAPI application.
    
    This function provides a standard interface for Manager integration.
    
    Returns:
        Configured FastAPI application
    """
    return app


def integrate_with_manager_api(manager_app: FastAPI, prefix: str = "/database-decommissioning"):
    """
    Integrate database decommissioning routes with the main Manager API.
    
    Args:
        manager_app: Main Manager FastAPI application
        prefix: URL prefix for database decommissioning routes
    """
    try:
        # Mount the database decommissioning app as a sub-application
        manager_app.mount(prefix, app)
        logger.info(f"Database decommissioning integrated with Manager API at {prefix}")
        
    except Exception as e:
        logger.error(f"Failed to integrate with Manager API: {e}")
        raise


# For development and testing
if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info",
    )