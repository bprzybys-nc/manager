"""
Manager API Patterns - Comprehensive Examples for Ovora Manager Component

This file demonstrates the standard patterns and practices for developing
FastAPI endpoints in the Ovora Manager component.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from src.database.client import DatabaseClient
from src.config import get_config
from src.modules.incident.db import IncidentDB

# Configure logging
logger = logging.getLogger(__name__)

# Data Models - Use Pydantic for validation
class IncidentRequest(BaseModel):
    """Request model for incident creation."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    severity: str = Field(..., regex="^(low|medium|high|critical)$")
    source: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Ensure metadata is JSON serializable."""
        if v is None:
            return {}
        # Add custom validation logic here
        return v

class IncidentResponse(BaseModel):
    """Response model for incident operations."""
    id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Router setup
router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

# Dependency injection
async def get_database() -> DatabaseClient:
    """Database dependency with proper cleanup."""
    config = get_config()
    async with DatabaseClient(config.mongo_db_uri) as db:
        yield db

async def get_incident_db(db: DatabaseClient = Depends(get_database)) -> IncidentDB:
    """Incident database dependency."""
    return IncidentDB(db)

# API Endpoints with comprehensive patterns

@router.post("/", response_model=IncidentResponse)
async def create_incident(
    request: IncidentRequest,
    background_tasks: BackgroundTasks,
    incident_db: IncidentDB = Depends(get_incident_db)
):
    """
    Create a new incident.
    
    This endpoint demonstrates:
    - Pydantic request/response models
    - Proper error handling
    - Database operations
    - Background task processing
    - Structured logging
    """
    try:
        logger.info(f"Creating incident: {request.title}")
        
        # Validate business logic
        if request.severity == "critical" and not request.metadata.get("escalation_contact"):
            raise HTTPException(
                status_code=400,
                detail="Critical incidents require escalation contact"
            )
        
        # Create incident
        incident_data = {
            "title": request.title,
            "description": request.description,
            "severity": request.severity,
            "source": request.source,
            "status": "open",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": request.metadata
        }
        
        incident_id = await incident_db.create_incident(incident_data)
        
        # Background task for notifications
        background_tasks.add_task(
            send_incident_notification,
            incident_id,
            request.severity
        )
        
        # Retrieve created incident
        incident = await incident_db.get_incident(incident_id)
        
        logger.info(f"Created incident {incident_id}")
        return IncidentResponse(**incident)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create incident: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create incident: {str(e)}"
        )

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    incident_db: IncidentDB = Depends(get_incident_db)
):
    """
    Get incident by ID.
    
    Demonstrates:
    - Path parameter handling
    - 404 error handling
    - Response model usage
    """
    try:
        logger.info(f"Retrieving incident: {incident_id}")
        
        incident = await incident_db.get_incident(incident_id)
        
        if not incident:
            raise HTTPException(
                status_code=404,
                detail=f"Incident {incident_id} not found"
            )
        
        return IncidentResponse(**incident)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve incident {incident_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve incident: {str(e)}"
        )

@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    incident_db: IncidentDB = Depends(get_incident_db)
):
    """
    List incidents with filtering and pagination.
    
    Demonstrates:
    - Query parameters
    - Filtering
    - Pagination
    - List response models
    """
    try:
        logger.info(f"Listing incidents: skip={skip}, limit={limit}")
        
        # Build filter
        filters = {}
        if severity:
            filters["severity"] = severity
        if status:
            filters["status"] = status
        
        # Get incidents
        incidents = await incident_db.list_incidents(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return [IncidentResponse(**incident) for incident in incidents]
        
    except Exception as e:
        logger.error(f"Failed to list incidents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list incidents: {str(e)}"
        )

# Health check endpoint
@router.get("/health")
async def health_check(db: DatabaseClient = Depends(get_database)):
    """
    Health check endpoint.
    
    Demonstrates:
    - Health check patterns
    - Database connectivity checks
    - Status reporting
    """
    try:
        # Check database connectivity
        await db.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "service": "incidents-api",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

# Background task functions
async def send_incident_notification(incident_id: str, severity: str):
    """Send notification for new incident."""
    try:
        logger.info(f"Sending notification for incident {incident_id}")
        
        # Implementation would integrate with Slack/email
        # This is a placeholder for the actual notification logic
        
        if severity == "critical":
            # Send urgent notification
            pass
        else:
            # Send normal notification
            pass
            
    except Exception as e:
        logger.error(f"Failed to send notification for {incident_id}: {str(e)}")

# Error handler examples
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions consistently."""
    return ErrorResponse(
        error=f"HTTP {exc.status_code}",
        message=exc.detail,
        details={"status_code": exc.status_code}
    )

@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return ErrorResponse(
        error="Internal Server Error",
        message="An unexpected error occurred",
        details={"type": type(exc).__name__}
    )

# Example of middleware usage
@router.middleware("http")
async def add_process_time_header(request, call_next):
    """Add processing time to response headers."""
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    return response