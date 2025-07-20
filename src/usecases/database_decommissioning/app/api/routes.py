"""
FastAPI Routes for Database Decommissioning Use Case.

This module provides Manager-integrated API endpoints for database decommissioning
workflows while maintaining GraphMCP framework compatibility.

Manager Integration:
- Standard Manager API patterns and route structure
- Tenant-aware workflow execution
- Database client integration for state persistence
- Celery task integration for background processing

GraphMCP Preservation:
- Full GraphMCP workflow orchestration
- Standard workflow configuration patterns
- MCP client integration
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from celery import Celery
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

# Manager imports
from src.database.client import DatabaseClient
from src.modules.task.db import TaskDB

# Local imports
from ..models import (
    DatabaseDecommissionRequest,
    DatabaseDecommissionResponse,
    WorkflowConfig, 
    WorkflowExecutionResult,
)
from ..orchestrator import DatabaseDecommissionOrchestrator
from ..utils import create_logger_for_workflow, validate_environment_dependencies
from ..validation.environment_validation import EnvironmentValidator
from ..validation.workflow_validation import WorkflowValidator


# Response models for API endpoints
class WorkflowExecuteRequest(BaseModel):
    """Request model for workflow execution."""
    database_name: str = Field(..., description="Name of the database to decommission")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenancy")
    user_id: Optional[str] = Field(None, description="User identifier")
    dry_run: bool = Field(False, description="Whether to perform a dry run without making changes")
    slack_channel: Optional[str] = Field(None, description="Slack channel for notifications")
    mcp_config_path: Optional[str] = Field(None, description="Path to MCP configuration file")
    # Workflow configuration
    max_parallel_steps: int = Field(4, description="Maximum parallel steps in workflow")
    default_timeout: int = Field(300, description="Default timeout for steps in seconds")
    stop_on_error: bool = Field(False, description="Whether to stop workflow on first error")


class WorkflowListResponse(BaseModel):
    """Response model for workflow listing."""
    workflows: List[Dict[str, Any]]
    total_count: int
    offset: int
    limit: int


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: str
    status: str
    database_name: Optional[str] = None
    tenant_id: Optional[str] = None
    repository: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    progress: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""
    status: str
    timestamp: float
    service: str
    version: str
    error: Optional[str] = None
    checks: Dict[str, Any] = {}


class DatabaseDecommissioningRoute:
    """
    Database decommissioning API routes with Manager integration.
    
    Provides FastAPI endpoints for executing and managing database decommissioning
    workflows while maintaining GraphMCP framework compatibility.
    """

    def __init__(
        self,
        db_client: DatabaseClient,
        task_db: Optional[TaskDB] = None,
        celery_app: Optional[Celery] = None,
    ):
        """
        Initialize database decommissioning routes.

        Args:
            db_client: Manager database client
            task_db: Optional task database for integration
            celery_app: Optional Celery app for background tasks
        """
        self.router = APIRouter()
        self.db_client = db_client
        self.task_db = task_db
        self.celery_app = celery_app
        
        # Workflow tracking
        self.active_workflows: Dict[str, DatabaseDecommissionOrchestrator] = {}
        
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes."""
        # Core workflow endpoints
        self.router.post("/execute", response_model=WorkflowExecutionResult)(self.execute_workflow)
        self.router.post("/execute/async", response_model=Dict[str, str])(self.execute_workflow_async)
        
        # Status and monitoring endpoints
        self.router.get("/workflows", response_model=WorkflowListResponse)(self.list_workflows)
        self.router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)(self.get_workflow_status)
        self.router.get("/workflows/{workflow_id}/result", response_model=WorkflowExecutionResult)(self.get_workflow_result)
        self.router.delete("/workflows/{workflow_id}")(self.cancel_workflow)
        
        # Validation endpoints
        self.router.get("/validate/environment", response_model=Dict[str, Any])(self.validate_environment)
        self.router.post("/validate/config", response_model=Dict[str, Any])(self.validate_workflow_config)
        
        # Health and diagnostics
        self.router.get("/health", response_model=HealthCheckResponse)(self.health_check)
        self.router.get("/health/detailed", response_model=Dict[str, Any])(self.detailed_health_check)

    async def execute_workflow(self, request: WorkflowExecuteRequest) -> WorkflowExecutionResult:
        """
        Execute database decommissioning workflow synchronously.

        Args:
            request: Workflow execution request

        Returns:
            Complete workflow execution result

        Raises:
            HTTPException: If workflow execution fails
        """
        try:
            # Create workflow configuration
            config = WorkflowConfig(
                database_name=request.database_name,
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                dry_run=request.dry_run,
                slack_channel=request.slack_channel,
                max_parallel_steps=request.max_parallel_steps,
                default_timeout=request.default_timeout,
                stop_on_error=request.stop_on_error,
            )

            # Execute workflow
            async with DatabaseDecommissionOrchestrator(
                config, request.mcp_config_path
            ) as orchestrator:
                # Track active workflow
                self.active_workflows[orchestrator.workflow_id] = orchestrator
                
                try:
                    result = await orchestrator.execute_workflow()
                    return result
                finally:
                    # Remove from active workflows
                    self.active_workflows.pop(orchestrator.workflow_id, None)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

    async def execute_workflow_async(
        self, request: WorkflowExecuteRequest, background_tasks: BackgroundTasks
    ) -> Dict[str, str]:
        """
        Execute database decommissioning workflow asynchronously.

        Args:
            request: Workflow execution request
            background_tasks: FastAPI background tasks

        Returns:
            Workflow ID and execution status
        """
        try:
            # Create workflow configuration
            config = WorkflowConfig(
                database_name=request.database_name,
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                dry_run=request.dry_run,
                slack_channel=request.slack_channel,
                max_parallel_steps=request.max_parallel_steps,
                default_timeout=request.default_timeout,
                stop_on_error=request.stop_on_error,
            )

            # Create orchestrator
            orchestrator = DatabaseDecommissionOrchestrator(config, request.mcp_config_path)
            
            # Track active workflow
            workflow_id = orchestrator.workflow_id
            self.active_workflows[workflow_id] = orchestrator

            # Execute workflow in background
            background_tasks.add_task(self._execute_workflow_background, orchestrator)

            return {
                "workflow_id": workflow_id,
                "status": "started",
                "database_name": request.database_name,
                "repository": f"{request.repo_owner}/{request.repo_name}",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

    async def _execute_workflow_background(self, orchestrator: DatabaseDecommissionOrchestrator):
        """Execute workflow in background task."""
        try:
            async with orchestrator:
                await orchestrator.execute_workflow()
        except Exception as e:
            # Log error but don't raise - this is a background task
            logger = create_logger_for_workflow(
                orchestrator.workflow_id, 
                orchestrator.config.database_name,
                orchestrator.config.tenant_id
            )
            logger.log_error(f"Background workflow execution failed", e)
        finally:
            # Remove from active workflows
            self.active_workflows.pop(orchestrator.workflow_id, None)

    async def list_workflows(
        self,
        tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
        database_name: Optional[str] = Query(None, description="Filter by database name"),
        status: Optional[str] = Query(None, description="Filter by workflow status"),
        limit: int = Query(50, description="Maximum number of workflows to return"),
        offset: int = Query(0, description="Offset for pagination"),
    ) -> WorkflowListResponse:
        """
        List database decommissioning workflows.

        Args:
            tenant_id: Optional tenant filter
            database_name: Optional database name filter
            status: Optional status filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of workflows with metadata
        """
        try:
            # Build query filters
            query_filter = {"workflow_type": "database_decommissioning"}
            
            if tenant_id:
                query_filter["tenant_id"] = tenant_id
            if database_name:
                query_filter["database_name"] = database_name
            if status:
                query_filter["status"] = status

            # Query database
            collection = self.db_client.database["workflow_executions"]
            
            # Get total count
            total_count = await collection.count_documents(query_filter)
            
            # Get workflows with pagination
            cursor = collection.find(query_filter).sort("created_at", -1).skip(offset).limit(limit)
            workflows = await cursor.to_list(length=limit)

            # Include active workflows
            active_workflows = []
            for workflow_id, orchestrator in self.active_workflows.items():
                if tenant_id and orchestrator.config.tenant_id != tenant_id:
                    continue
                if database_name and orchestrator.config.database_name != database_name:
                    continue
                
                active_workflows.append({
                    "workflow_id": workflow_id,
                    "database_name": orchestrator.config.database_name,
                    "tenant_id": orchestrator.config.tenant_id,
                    "status": "running",
                    "created_at": time.time(),
                    "repository": f"{orchestrator.config.repo_owner}/{orchestrator.config.repo_name}",
                })

            return WorkflowListResponse(
                workflows=workflows + active_workflows,
                total_count=total_count + len(active_workflows),
                offset=offset,
                limit=limit,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")

    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatusResponse:
        """
        Get workflow execution status.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow status and metadata

        Raises:
            HTTPException: If workflow not found
        """
        try:
            # Check active workflows first
            if workflow_id in self.active_workflows:
                orchestrator = self.active_workflows[workflow_id]
                return WorkflowStatusResponse(
                    workflow_id=workflow_id,
                    status="running",
                    database_name=orchestrator.config.database_name,
                    tenant_id=orchestrator.config.tenant_id,
                    repository=f"{orchestrator.config.repo_owner}/{orchestrator.config.repo_name}",
                    created_at=time.time(),
                    progress={
                        "current_step": "executing",
                        "total_steps": "unknown",
                        "completion_percentage": None,
                    }
                )

            # Query database for completed workflows
            collection = self.db_client.database["workflow_executions"]
            workflow = await collection.find_one({"workflow_id": workflow_id})

            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

            return WorkflowStatusResponse(
                workflow_id=workflow_id,
                status="completed" if workflow.get("success") else "failed",
                database_name=workflow.get("database_name"),
                tenant_id=workflow.get("tenant_id"),
                repository=workflow.get("config", {}).get("repository"),
                created_at=workflow.get("created_at"),
                completed_at=workflow.get("created_at", 0) + workflow.get("duration", 0),
                duration=workflow.get("duration"),
                success=workflow.get("success"),
                summary=workflow.get("summary", {}),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

    async def get_workflow_result(self, workflow_id: str) -> WorkflowExecutionResult:
        """
        Get complete workflow execution result.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Complete workflow execution result

        Raises:
            HTTPException: If workflow not found or still running
        """
        try:
            # Check if workflow is still running
            if workflow_id in self.active_workflows:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Workflow {workflow_id} is still running"
                )

            # Query database for completed workflow
            collection = self.db_client.database["workflow_executions"]
            workflow = await collection.find_one({"workflow_id": workflow_id})

            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

            # Convert to WorkflowExecutionResult
            return WorkflowExecutionResult(
                workflow_id=workflow_id,
                database_name=workflow.get("database_name"),
                success=workflow.get("success", False),
                duration=workflow.get("duration", 0),
                step_results=workflow.get("step_results", {}),
                tenant_id=workflow.get("tenant_id"),
                user_id=workflow.get("user_id"),
                config=workflow.get("config", {}),
                summary=workflow.get("summary", {}),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get workflow result: {str(e)}")

    async def cancel_workflow(self, workflow_id: str) -> Dict[str, str]:
        """
        Cancel running workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Cancellation status

        Raises:
            HTTPException: If workflow not found or cannot be cancelled
        """
        try:
            if workflow_id not in self.active_workflows:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Active workflow {workflow_id} not found"
                )

            # Remove from active workflows (this will stop tracking)
            orchestrator = self.active_workflows.pop(workflow_id)
            
            # Close orchestrator resources
            await orchestrator.close()

            return {
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow has been cancelled"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")

    async def validate_environment(self) -> Dict[str, Any]:
        """
        Validate environment for database decommissioning workflows.

        Returns:
            Environment validation results
        """
        try:
            validator = EnvironmentValidator("env_validation")
            return validator.validate_environment()

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Environment validation failed: {str(e)}")

    async def validate_workflow_config(self, request: WorkflowExecuteRequest) -> Dict[str, Any]:
        """
        Validate workflow configuration.

        Args:
            request: Workflow configuration to validate

        Returns:
            Configuration validation results
        """
        try:
            # Create config from request
            config = WorkflowConfig(
                database_name=request.database_name,
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                dry_run=request.dry_run,
                slack_channel=request.slack_channel,
                max_parallel_steps=request.max_parallel_steps,
                default_timeout=request.default_timeout,
                stop_on_error=request.stop_on_error,
            )

            # Validate configuration
            validator = WorkflowValidator("config_validation")
            return validator.validate_workflow_configuration(config)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")

    async def health_check(self) -> HealthCheckResponse:
        """
        Basic health check for database decommissioning service.

        Returns:
            Service health status
        """
        try:
            # Check database connectivity
            db_healthy = bool(self.db_client and await self._check_database_health())
            
            # Check active workflows
            active_count = len(self.active_workflows)

            return HealthCheckResponse(
                status="healthy" if db_healthy else "unhealthy",
                timestamp=time.time(),
                service="database_decommissioning",
                version="1.0.0",
                checks={
                    "database": "healthy" if db_healthy else "unhealthy",
                    "active_workflows": active_count,
                    "mcp_clients": "available",
                }
            )

        except Exception as e:
            return HealthCheckResponse(
                status="unhealthy",
                timestamp=time.time(),
                service="database_decommissioning",
                version="1.0.0",
                error=str(e),
                checks={}
            )

    async def detailed_health_check(self) -> Dict[str, Any]:
        """
        Detailed health check with component status.

        Returns:
            Comprehensive health status
        """
        try:
            health_data = {
                "service": "database_decommissioning",
                "timestamp": time.time(),
                "status": "healthy",
                "components": {},
                "active_workflows": len(self.active_workflows),
                "workflow_details": []
            }

            # Check database
            try:
                db_healthy = await self._check_database_health()
                health_data["components"]["database"] = {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "connected": db_healthy,
                }
            except Exception as e:
                health_data["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_data["status"] = "degraded"

            # Check environment
            try:
                validator = EnvironmentValidator("health_check")
                env_result = validator.validate_environment()
                health_data["components"]["environment"] = {
                    "status": "healthy" if env_result.get("overall_success") else "degraded",
                    "details": env_result,
                }
                if not env_result.get("overall_success"):
                    health_data["status"] = "degraded"
            except Exception as e:
                health_data["components"]["environment"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_data["status"] = "degraded"

            # Add active workflow details
            for workflow_id, orchestrator in self.active_workflows.items():
                health_data["workflow_details"].append({
                    "workflow_id": workflow_id,
                    "database_name": orchestrator.config.database_name,
                    "tenant_id": orchestrator.config.tenant_id,
                    "repository": f"{orchestrator.config.repo_owner}/{orchestrator.config.repo_name}",
                })

            return health_data

        except Exception as e:
            return {
                "service": "database_decommissioning",
                "timestamp": time.time(),
                "status": "unhealthy",
                "error": str(e),
                "components": {},
            }

    async def _check_database_health(self) -> bool:
        """Check database connectivity."""
        try:
            if not self.db_client:
                return False
            
            # Try to ping the database
            await self.db_client.database.command("ping")
            return True
        except Exception:
            return False


# Factory function for creating routes
def create_database_decommissioning_routes(
    db_client: DatabaseClient,
    task_db: Optional[TaskDB] = None,
    celery_app: Optional[Celery] = None,
) -> DatabaseDecommissioningRoute:
    """
    Factory function to create database decommissioning routes.

    Args:
        db_client: Manager database client
        task_db: Optional task database for integration
        celery_app: Optional Celery app for background tasks

    Returns:
        Initialized database decommissioning routes
    """
    return DatabaseDecommissioningRoute(db_client, task_db, celery_app)


# Legacy compatibility for Manager API integration
async def get_database_decommissioning_router(
    db_client: DatabaseClient,
    task_db: Optional[TaskDB] = None,
    celery_app: Optional[Celery] = None,
) -> APIRouter:
    """
    Get database decommissioning API router for Manager integration.

    Args:
        db_client: Manager database client
        task_db: Optional task database
        celery_app: Optional Celery app

    Returns:
        Configured API router
    """
    route_handler = create_database_decommissioning_routes(db_client, task_db, celery_app)
    return route_handler.router