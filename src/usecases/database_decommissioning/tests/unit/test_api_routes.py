"""
Unit tests for database decommissioning API routes.

Tests the FastAPI route implementations with Manager integration patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.routes import DatabaseDecommissioningRoute
from app.models import (
    WorkflowExecutionRequest,
    WorkflowExecutionResultResponse,
    WorkflowExecutionResult,
    WorkflowConfig,
)


@pytest.mark.unit
class TestDatabaseDecommissioningRoute:
    """Test DatabaseDecommissioningRoute class."""

    def test_route_initialization(self, mock_database_client):
        """Test route initialization."""
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
        )
        
        assert route.db_client == mock_database_client
        assert route.task_db is None
        assert route.celery_app is None
        assert route.router is not None

    def test_route_with_task_db(self, mock_database_client):
        """Test route initialization with task database."""
        mock_task_db = Mock()
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            task_db=mock_task_db,
        )
        
        assert route.task_db == mock_task_db

    def test_route_with_celery(self, mock_database_client):
        """Test route initialization with Celery."""
        mock_celery = Mock()
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=mock_celery,
        )
        
        assert route.celery_app == mock_celery


@pytest.mark.unit
@pytest.mark.asyncio
class TestSyncDecommissionEndpoint:
    """Test synchronous decommission endpoint."""

    async def test_sync_decommission_success(self, mock_database_client, postgres_air_database):
        """Test successful synchronous decommissioning."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        # Mock successful orchestrator execution
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=True,
                duration_seconds=5.0,
                steps_completed=5,
                total_steps=5,
                discovery_result={"files": []},
                validation_results=[],
                final_recommendations=["Success"],
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.sync_decommission(request)
            
            assert isinstance(response, DatabaseDecommissionResponse)
            assert response.status == "completed"
            assert response.workflow_id == "test_workflow_123"
            assert response.result is not None

    async def test_sync_decommission_failure(self, mock_database_client, postgres_air_database):
        """Test synchronous decommissioning with failure."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        # Mock failed orchestrator execution
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=False,
                duration_seconds=2.0,
                steps_completed=2,
                total_steps=5,
                discovery_result={"error": "Discovery failed"},
                validation_results=[],
                final_recommendations=["Check configuration"],
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.sync_decommission(request)
            
            assert isinstance(response, DatabaseDecommissionResponse)
            assert response.status == "failed"
            assert response.workflow_id == "test_workflow_123"
            assert "Discovery failed" in str(response.result)

    async def test_sync_decommission_exception(self, mock_database_client, postgres_air_database):
        """Test synchronous decommissioning with exception."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        # Mock orchestrator that raises exception
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_workflow = AsyncMock(
                side_effect=Exception("Orchestrator error")
            )
            mock_orchestrator_class.return_value = mock_orchestrator
            
            with pytest.raises(HTTPException) as exc_info:
                await route.sync_decommission(request)
            
            assert exc_info.value.status_code == 500
            assert "Orchestrator error" in str(exc_info.value.detail)

    async def test_sync_decommission_tenant_context(self, mock_database_client, postgres_air_database, test_tenant_id):
        """Test synchronous decommissioning with tenant context."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        # Mock successful orchestrator execution
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=True,
                duration_seconds=3.0,
                steps_completed=3,
                total_steps=3,
                discovery_result={"files": []},
                validation_results=[],
                final_recommendations=["Success"],
                execution_context={
                    "tenant_id": test_tenant_id,
                    "user_id": "test_user",
                },
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.sync_decommission(request)
            
            # Verify tenant context is preserved
            assert response.result["execution_context"]["tenant_id"] == test_tenant_id
            assert response.result["execution_context"]["user_id"] == "test_user"


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncDecommissionEndpoint:
    """Test asynchronous decommission endpoint."""

    async def test_async_decommission_with_celery(self, mock_database_client, postgres_air_database):
        """Test asynchronous decommissioning with Celery."""
        mock_celery = Mock()
        mock_task = Mock()
        mock_task.id = "task_123"
        mock_celery.send_task.return_value = mock_task
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=mock_celery,
        )
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            async_execution=True,
        )
        
        response = await route.async_decommission(request)
        
        assert isinstance(response, DatabaseDecommissionResponse)
        assert response.status == "queued"
        assert response.workflow_id == "task_123"
        assert "queued for processing" in response.message

    async def test_async_decommission_without_celery(self, mock_database_client, postgres_air_database):
        """Test asynchronous decommissioning without Celery (fallback to sync)."""
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=None,  # No Celery
        )
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            async_execution=True,
        )
        
        # Mock successful orchestrator execution (fallback to sync)
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=True,
                duration_seconds=4.0,
                steps_completed=4,
                total_steps=4,
                discovery_result={"files": []},
                validation_results=[],
                final_recommendations=["Success"],
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.async_decommission(request)
            
            assert response.status == "completed"  # Completed synchronously
            assert response.workflow_id == "test_workflow_123"

    async def test_async_decommission_celery_exception(self, mock_database_client, postgres_air_database):
        """Test asynchronous decommissioning with Celery exception."""
        mock_celery = Mock()
        mock_celery.send_task.side_effect = Exception("Celery error")
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=mock_celery,
        )
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            async_execution=True,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await route.async_decommission(request)
        
        assert exc_info.value.status_code == 500
        assert "Celery error" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.asyncio
class TestWorkflowStatusEndpoint:
    """Test workflow status endpoint."""

    async def test_get_workflow_status_running(self, mock_database_client):
        """Test getting status of running workflow."""
        mock_task_db = Mock()
        mock_task_db.get_task_status = AsyncMock(
            return_value={
                "task_id": "task_123",
                "status": "PROGRESS",
                "result": {"current_step": "validation", "progress": 60},
            }
        )
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            task_db=mock_task_db,
        )
        
        response = await route.get_workflow_status("task_123")
        
        assert isinstance(response, DatabaseDecommissionResponse)
        assert response.status == "running"
        assert response.workflow_id == "task_123"
        assert "60%" in response.message

    async def test_get_workflow_status_completed(self, mock_database_client):
        """Test getting status of completed workflow."""
        mock_task_db = Mock()
        mock_task_db.get_task_status = AsyncMock(
            return_value={
                "task_id": "task_123",
                "status": "SUCCESS",
                "result": {
                    "workflow_id": "task_123",
                    "success": True,
                    "duration_seconds": 10.0,
                },
            }
        )
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            task_db=mock_task_db,
        )
        
        response = await route.get_workflow_status("task_123")
        
        assert response.status == "completed"
        assert response.result["success"] is True

    async def test_get_workflow_status_not_found(self, mock_database_client):
        """Test getting status of non-existent workflow."""
        mock_task_db = Mock()
        mock_task_db.get_task_status = AsyncMock(return_value=None)
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            task_db=mock_task_db,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await route.get_workflow_status("nonexistent_task")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    async def test_get_workflow_status_no_task_db(self, mock_database_client):
        """Test getting status without task database."""
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            task_db=None,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await route.get_workflow_status("task_123")
        
        assert exc_info.value.status_code == 501
        assert "not implemented" in str(exc_info.value.detail).lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestHealthCheckEndpoint:
    """Test health check endpoint."""

    async def test_health_check_healthy(self, mock_database_client):
        """Test health check with healthy services."""
        # Mock healthy database
        mock_database_client.database.admin.command = AsyncMock(
            return_value={"ok": 1}
        )
        
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        with patch('...app.api.routes.validate_environment_dependencies') as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "available_services": ["database_client", "azure_openai"],
                "missing_services": [],
            }
            
            response = await route.health_check()
            
            assert response["status"] == "healthy"
            assert response["database"]["status"] == "healthy"
            assert len(response["dependencies"]["available_services"]) > 0

    async def test_health_check_unhealthy_database(self, mock_database_client):
        """Test health check with unhealthy database."""
        # Mock unhealthy database
        mock_database_client.database.admin.command = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        with patch('...app.api.routes.validate_environment_dependencies') as mock_validate:
            mock_validate.return_value = {
                "success": False,
                "available_services": [],
                "missing_services": ["database_client", "azure_openai"],
            }
            
            response = await route.health_check()
            
            assert response["status"] == "unhealthy"
            assert response["database"]["status"] == "unhealthy"

    async def test_health_check_no_database(self):
        """Test health check without database client."""
        route = DatabaseDecommissioningRoute(db_client=None)
        
        with patch('...app.api.routes.validate_environment_dependencies') as mock_validate:
            mock_validate.return_value = {
                "success": False,
                "available_services": [],
                "missing_services": ["database_client"],
            }
            
            response = await route.health_check()
            
            assert response["status"] == "degraded"
            assert response["database"]["status"] == "unavailable"


@pytest.mark.unit
@pytest.mark.asyncio
class TestDetailedHealthCheckEndpoint:
    """Test detailed health check endpoint."""

    async def test_detailed_health_check_complete(self, mock_database_client):
        """Test detailed health check with all components."""
        mock_celery = Mock()
        mock_celery.control.inspect.return_value.active.return_value = {"worker1": []}
        
        mock_task_db = Mock()
        mock_task_db.get_connection_status = AsyncMock(return_value={"status": "connected"})
        
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=mock_celery,
            task_db=mock_task_db,
        )
        
        # Mock healthy database
        mock_database_client.database.admin.command = AsyncMock(
            return_value={"ok": 1}
        )
        
        with patch('...app.api.routes.validate_environment_dependencies') as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "available_services": ["database_client", "azure_openai"],
                "missing_services": [],
                "service_details": {
                    "database_client": {"status": "connected"},
                    "azure_openai": {"status": "available"},
                },
            }
            
            response = await route.detailed_health_check()
            
            assert response["status"] == "healthy"
            assert "database" in response
            assert "celery" in response
            assert "task_db" in response
            assert "dependencies" in response

    async def test_detailed_health_check_celery_unavailable(self, mock_database_client):
        """Test detailed health check with Celery unavailable."""
        route = DatabaseDecommissioningRoute(
            db_client=mock_database_client,
            celery_app=None,  # No Celery
        )
        
        # Mock healthy database
        mock_database_client.database.admin.command = AsyncMock(
            return_value={"ok": 1}
        )
        
        with patch('...app.api.routes.validate_environment_dependencies') as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "available_services": ["database_client"],
                "missing_services": ["celery"],
            }
            
            response = await route.detailed_health_check()
            
            assert response["celery"]["status"] == "unavailable"


@pytest.mark.unit
@pytest.mark.manager
class TestManagerIntegrationFeatures:
    """Test Manager-specific API route features."""

    async def test_tenant_aware_request_processing(self, mock_database_client, postgres_air_database, test_tenant_id):
        """Test tenant-aware request processing."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        # Mock orchestrator to verify tenant context
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=True,
                duration_seconds=2.0,
                steps_completed=2,
                total_steps=2,
                discovery_result={"files": []},
                validation_results=[],
                final_recommendations=["Success"],
                execution_context={
                    "tenant_id": test_tenant_id,
                    "user_id": "test_user",
                },
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.sync_decommission(request)
            
            # Verify orchestrator was created with tenant-aware config
            args, kwargs = mock_orchestrator_class.call_args
            config = kwargs.get('config') or args[0] if args else None
            
            assert config is not None
            assert config.tenant_id == test_tenant_id
            assert config.user_id == "test_user"

    async def test_error_handling_with_tenant_context(self, mock_database_client, postgres_air_database, test_tenant_id):
        """Test error handling preserves tenant context."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
        )
        
        # Mock orchestrator that fails
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_workflow = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_orchestrator_class.return_value = mock_orchestrator
            
            with pytest.raises(HTTPException) as exc_info:
                await route.sync_decommission(request)
            
            # Error should include tenant context for debugging
            error_detail = str(exc_info.value.detail)
            assert test_tenant_id in error_detail or "tenant" in error_detail.lower()

    def test_pydantic_request_validation(self, mock_database_client):
        """Test Pydantic request validation."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        # Test invalid request (missing required fields)
        with pytest.raises(ValueError):
            DatabaseDecommissionRequest()
        
        # Test invalid data types
        with pytest.raises(ValueError):
            DatabaseDecommissionRequest(
                database_name=123,  # Should be string
                repo_owner="test",
                repo_name="test",
            )

    async def test_response_serialization(self, mock_database_client, postgres_air_database):
        """Test response serialization for Manager API consistency."""
        route = DatabaseDecommissioningRoute(db_client=mock_database_client)
        
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        # Mock successful execution
        with patch('...app.api.routes.DatabaseDecommissionOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_result = WorkflowExecutionResult(
                workflow_id="test_workflow_123",
                database_name=postgres_air_database,
                success=True,
                duration_seconds=1.0,
                steps_completed=1,
                total_steps=1,
                discovery_result={"files": []},
                validation_results=[],
                final_recommendations=["Success"],
            )
            mock_orchestrator.execute_workflow = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            response = await route.sync_decommission(request)
            
            # Test serialization to JSON
            json_data = response.model_dump_json()
            assert isinstance(json_data, str)
            assert postgres_air_database in json_data
            
            # Test dict conversion
            dict_data = response.model_dump()
            assert isinstance(dict_data, dict)
            assert dict_data["workflow_id"] == "test_workflow_123"