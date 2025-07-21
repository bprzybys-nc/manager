"""
Microservice Patterns - Manager Component Examples

This file demonstrates patterns for creating microservice tools within the
Ovora Manager component, following the established patterns from existing tools.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
import logging
import httpx
import asyncio
from datetime import datetime
import uuid
from contextlib import asynccontextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Standard FastAPI Application Pattern
def create_microservice_app(
    title: str,
    description: str,
    version: str = "1.0.0"
) -> FastAPI:
    """
    Create a standardized FastAPI application for Manager microservices.
    
    This pattern is used across all Manager microservice tools:
    - Confluence tool (src/tools/confluence/)
    - Jira tool (src/tools/jira/)
    - CMD Exec tool (src/tools/cmd_exec/)
    
    Args:
        title: Service name
        description: Service description
        version: Service version
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware for cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request ID middleware for tracking
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add request ID for request tracking."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        logger.info(
            f"Request completed: {response.status_code}",
            extra={"request_id": request_id}
        )
        
        return response
    
    return app

# Standard Data Models Pattern
class BaseServiceRequest(BaseModel):
    """Base request model for microservice operations."""
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    timeout: Optional[int] = Field(30, ge=1, le=300, description="Request timeout in seconds")

class BaseServiceResponse(BaseModel):
    """Base response model for microservice operations."""
    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Optional[Dict[str, str]] = Field(None, description="Dependency health status")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    code: int = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request ID")

# External Service Client Pattern
class BaseExternalClient:
    """
    Base pattern for external service clients.
    
    This pattern is used in:
    - Confluence client (src/tools/confluence/app/confluence.py)
    - Jira client (src/tools/jira/app/jira.py)
    - Database clients (src/tools/db_servers_cmdb/app/db.py)
    """
    
    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @asynccontextmanager
    async def _get_client(self):
        """Get or create HTTP client with proper resource management."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                auth=(self.username, self.api_token),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Ovora-Manager/1.0'
                }
            )
        try:
            yield self._client
        finally:
            # Keep client alive for reuse - closed by lifespan
            pass
    
    async def close(self):
        """Close HTTP client - called during app shutdown."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """Check if external service is accessible."""
        try:
            async with self._get_client() as client:
                response = await client.get(f"{self.base_url}/status")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# Dependency Injection Pattern
def create_dependency_provider(client_class, config_prefix: str):
    """
    Create dependency provider for external service clients.
    
    Pattern used across Manager microservices for consistent
    dependency injection and configuration management.
    
    Args:
        client_class: External client class
        config_prefix: Configuration prefix (e.g., 'CONFLUENCE', 'JIRA')
        
    Returns:
        Dependency provider function
    """
    def get_client():
        from src.config import get_config
        config = get_config()
        
        return client_class(
            base_url=getattr(config, f"{config_prefix}_URL"),
            username=getattr(config, f"{config_prefix}_USERNAME"),
            api_token=getattr(config, f"{config_prefix}_API_TOKEN"),
            timeout=getattr(config, f"{config_prefix}_TIMEOUT", 30)
        )
    
    return get_client

# Standard Health Check Endpoints Pattern
def add_health_endpoints(app: FastAPI, service_name: str, external_client_provider):
    """
    Add standard health check endpoints to microservice.
    
    Pattern used across all Manager microservice tools:
    - /health - Basic health check
    - /health/ready - Readiness check with dependencies
    - /health/live - Liveness check
    """
    
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """Basic health check endpoint."""
        return HealthResponse(
            status="healthy",
            service=service_name
        )
    
    @app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
    async def readiness_check(client=Depends(external_client_provider)):
        """Readiness check with external service connectivity."""
        dependencies = {}
        overall_status = "ready"
        
        # Check external service connectivity
        try:
            is_healthy = await client.health_check()
            dependencies["external_service"] = "connected" if is_healthy else "disconnected"
            if not is_healthy:
                overall_status = "not_ready"
        except Exception as e:
            logger.error(f"External service check failed: {e}")
            dependencies["external_service"] = "error"
            overall_status = "not_ready"
        
        if overall_status != "ready":
            raise HTTPException(
                status_code=503,
                detail="Service not ready"
            )
        
        return HealthResponse(
            status=overall_status,
            service=service_name,
            dependencies=dependencies
        )
    
    @app.get("/health/live", response_model=HealthResponse, tags=["Health"])
    async def liveness_check():
        """Liveness check for container orchestration."""
        return HealthResponse(
            status="alive",
            service=service_name
        )

# Error Handling Pattern
def add_error_handlers(app: FastAPI):
    """
    Add standard error handlers for microservice.
    
    Pattern used across Manager microservices for consistent
    error handling and logging.
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTPException",
                detail=str(exc.detail),
                code=exc.status_code,
                request_id=request_id
            ).dict()
        )
    
    @app.exception_handler(httpx.HTTPStatusError)
    async def httpx_error_handler(request: Request, exc: httpx.HTTPStatusError):
        """Handle external service HTTP errors."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.error(
            f"External service error: {exc.response.status_code}",
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="ExternalServiceError",
                detail=f"External service returned {exc.response.status_code}",
                code=503,
                request_id=request_id
            ).dict()
        )
    
    @app.exception_handler(httpx.TimeoutException)
    async def timeout_handler(request: Request, exc: httpx.TimeoutException):
        """Handle timeout errors."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.error(
            "Request timeout",
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=504,
            content=ErrorResponse(
                error="TimeoutError",
                detail="Request timed out",
                code=504,
                request_id=request_id
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.error(
            f"Unexpected error: {exc}",
            extra={"request_id": request_id},
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="InternalServerError",
                detail="An unexpected error occurred",
                code=500,
                request_id=request_id
            ).dict()
        )

# CRUD Operations Pattern
def create_crud_endpoints(
    app: FastAPI,
    router_prefix: str,
    resource_name: str,
    request_model: BaseModel,
    response_model: BaseModel,
    client_dependency
):
    """
    Create standard CRUD endpoints for resource management.
    
    This pattern provides consistent CRUD operations across
    Manager microservices following REST conventions.
    """
    from fastapi import APIRouter
    
    router = APIRouter(prefix=router_prefix, tags=[resource_name.title()])
    
    @router.post(f"/{resource_name}", response_model=response_model)
    async def create_resource(
        request: request_model,
        background_tasks: BackgroundTasks,
        client=Depends(client_dependency)
    ):
        """Create new resource."""
        try:
            result = await client.create_resource(request.dict())
            
            # Schedule background tasks if needed
            background_tasks.add_task(log_resource_created, result)
            
            return response_model(
                success=True,
                data=result,
                message=f"{resource_name.title()} created successfully"
            )
        except Exception as e:
            logger.error(f"Error creating {resource_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create {resource_name}")
    
    @router.get(f"/{resource_name}/{{resource_id}}", response_model=response_model)
    async def get_resource(
        resource_id: str,
        client=Depends(client_dependency)
    ):
        """Get resource by ID."""
        try:
            resource = await client.get_resource(resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail=f"{resource_name.title()} not found")
            
            return response_model(
                success=True,
                data=resource,
                message=f"{resource_name.title()} retrieved successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving {resource_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve {resource_name}")
    
    @router.get(f"/{resource_name}", response_model=List[response_model])
    async def list_resources(
        limit: int = 50,
        offset: int = 0,
        client=Depends(client_dependency)
    ):
        """List resources with pagination."""
        try:
            resources = await client.list_resources(limit=limit, offset=offset)
            return [
                response_model(
                    success=True,
                    data=resource,
                    message="Success"
                )
                for resource in resources
            ]
        except Exception as e:
            logger.error(f"Error listing {resource_name}s: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list {resource_name}s")
    
    @router.put(f"/{resource_name}/{{resource_id}}", response_model=response_model)
    async def update_resource(
        resource_id: str,
        request: request_model,
        client=Depends(client_dependency)
    ):
        """Update existing resource."""
        try:
            result = await client.update_resource(resource_id, request.dict())
            if not result:
                raise HTTPException(status_code=404, detail=f"{resource_name.title()} not found")
            
            return response_model(
                success=True,
                data=result,
                message=f"{resource_name.title()} updated successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating {resource_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update {resource_name}")
    
    @router.delete(f"/{resource_name}/{{resource_id}}")
    async def delete_resource(
        resource_id: str,
        client=Depends(client_dependency)
    ):
        """Delete resource."""
        try:
            success = await client.delete_resource(resource_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"{resource_name.title()} not found")
            
            return {"message": f"{resource_name.title()} deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting {resource_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete {resource_name}")
    
    app.include_router(router)

# Background Job Management Pattern
class JobManager:
    """
    Background job management pattern used in Manager microservices.
    
    Based on patterns from:
    - Confluence tool job management
    - Database decommissioning workflows
    """
    
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
    
    def create_job(self, job_type: str, parameters: Dict[str, Any]) -> str:
        """Create new background job."""
        job_id = str(uuid.uuid4())
        
        self.jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "status": "pending",
            "progress": 0.0,
            "message": "Job created",
            "parameters": parameters,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }
        
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details."""
        return self.jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ):
        """Update job status and details."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if status:
            job["status"] = status
        if progress is not None:
            job["progress"] = progress
        if message:
            job["message"] = message
        if result is not None:
            job["result"] = result
        if error:
            job["error"] = error
        
        job["updated_at"] = datetime.utcnow()
        
        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")
        return True
    
    def list_jobs(self, job_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all jobs, optionally filtered by type."""
        jobs = list(self.jobs.values())
        
        if job_type:
            jobs = [job for job in jobs if job["type"] == job_type]
        
        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)

# Application Lifespan Pattern
def create_lifespan_handler(external_clients: List):
    """
    Create lifespan event handler for proper resource management.
    
    Pattern used for:
    - Database connection cleanup
    - HTTP client cleanup
    - Background task cleanup
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup
        logger.info("Starting up microservice")
        
        # Initialize external clients if needed
        for client in external_clients:
            if hasattr(client, 'initialize'):
                await client.initialize()
        
        yield
        
        # Shutdown
        logger.info("Shutting down microservice")
        
        # Cleanup external clients
        for client in external_clients:
            if hasattr(client, 'close'):
                await client.close()
    
    return lifespan

# Complete Microservice Factory Pattern
def create_complete_microservice(
    service_name: str,
    service_description: str,
    external_client_class,
    config_prefix: str,
    request_model: BaseModel,
    response_model: BaseModel,
    resource_name: str
) -> FastAPI:
    """
    Factory function to create a complete microservice following Manager patterns.
    
    This combines all the patterns above into a single, reusable factory
    that creates a fully-featured microservice with:
    - Health checks
    - Error handling
    - CRUD operations
    - Background jobs
    - Proper resource management
    
    Usage:
        app = create_complete_microservice(
            service_name="My Service",
            service_description="My service description",
            external_client_class=MyExternalClient,
            config_prefix="MY_SERVICE",
            request_model=MyRequest,
            response_model=MyResponse,
            resource_name="myresource"
        )
    """
    # Create FastAPI app
    app = create_microservice_app(
        title=service_name,
        description=service_description
    )
    
    # Create client dependency
    client_dependency = create_dependency_provider(
        external_client_class,
        config_prefix
    )
    
    # Add health endpoints
    add_health_endpoints(app, service_name, client_dependency)
    
    # Add error handlers
    add_error_handlers(app)
    
    # Add CRUD endpoints
    create_crud_endpoints(
        app=app,
        router_prefix="/api",
        resource_name=resource_name,
        request_model=request_model,
        response_model=response_model,
        client_dependency=client_dependency
    )
    
    # Add job management
    job_manager = JobManager()
    
    @app.get("/jobs/{job_id}")
    async def get_job_status(job_id: str):
        """Get job status."""
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    
    # Add lifespan handler
    external_clients = [client_dependency()]
    app.router.lifespan_context = create_lifespan_handler(external_clients)
    
    return app

# Helper Functions
async def log_resource_created(resource: Dict[str, Any]):
    """Background task to log resource creation."""
    logger.info(f"Resource created: {resource.get('id', 'unknown')}")

# Example Usage
if __name__ == "__main__":
    # Example of creating a complete microservice
    class ExampleRequest(BaseServiceRequest):
        name: str = Field(..., description="Resource name")
        description: Optional[str] = Field(None, description="Resource description")
    
    class ExampleResponse(BaseServiceResponse):
        data: Dict[str, Any] = Field(..., description="Response data")
    
    class ExampleClient(BaseExternalClient):
        async def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
            # Simulate creating resource
            return {"id": str(uuid.uuid4()), **data}
        
        async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
            # Simulate getting resource
            return {"id": resource_id, "name": "Example Resource"}
        
        async def list_resources(self, limit: int, offset: int) -> List[Dict[str, Any]]:
            # Simulate listing resources
            return [{"id": f"resource-{i}", "name": f"Resource {i}"} for i in range(limit)]
        
        async def update_resource(self, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
            # Simulate updating resource
            return {"id": resource_id, **data}
        
        async def delete_resource(self, resource_id: str) -> bool:
            # Simulate deleting resource
            return True
    
    app = create_complete_microservice(
        service_name="Example Service",
        service_description="Example microservice using Manager patterns",
        external_client_class=ExampleClient,
        config_prefix="EXAMPLE",
        request_model=ExampleRequest,
        response_model=ExampleResponse,
        resource_name="example"
    )
    
    # Run with: uvicorn microservices_patterns:app --reload