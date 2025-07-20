"""
Unit tests for database decommissioning data models.

Tests the data models with Manager integration while preserving GraphMCP compatibility.
"""

import pytest
from dataclasses import asdict
from typing import Dict, Any

from app.models import (
    WorkflowConfig,
    WorkflowExecutionResult,
    ValidationResult,
    QualityAssuranceResult,
    FileProcessingResult,
    WorkflowExecutionRequest,
    WorkflowExecutionResultResponse,
)


@pytest.mark.unit
class TestWorkflowConfig:
    """Test WorkflowConfig data model."""

    def test_basic_creation(self, postgres_air_database):
        """Test basic WorkflowConfig creation."""
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        assert config.database_name == postgres_air_database
        assert config.repo_owner == "test_owner"
        assert config.repo_name == "test_repo"
        assert config.tenant_id is None
        assert config.user_id is None
        assert config.max_parallel_steps == 4
        assert config.default_timeout == 120
        assert config.debug_mode is False

    def test_manager_integration_fields(self, postgres_air_database, test_tenant_id):
        """Test Manager-specific fields."""
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        assert config.tenant_id == test_tenant_id
        assert config.user_id == "test_user"

    def test_to_dict_conversion(self, postgres_air_database, test_tenant_id):
        """Test conversion to dictionary."""
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
            max_parallel_steps=8,
            debug_mode=True,
        )
        
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result["database_name"] == postgres_air_database
        assert result["tenant_id"] == test_tenant_id
        assert result["user_id"] == "test_user"
        assert result["max_parallel_steps"] == 8
        assert result["debug_mode"] is True

    def test_from_dict_creation(self, postgres_air_database, test_tenant_id):
        """Test creation from dictionary."""
        data = {
            "database_name": postgres_air_database,
            "repo_owner": "test_owner", 
            "repo_name": "test_repo",
            "tenant_id": test_tenant_id,
            "user_id": "test_user",
            "max_parallel_steps": 6,
            "debug_mode": True,
        }
        
        config = WorkflowConfig.from_dict(data)
        
        assert config.database_name == postgres_air_database
        assert config.tenant_id == test_tenant_id
        assert config.user_id == "test_user"
        assert config.max_parallel_steps == 6
        assert config.debug_mode is True

    def test_repo_url_property(self, postgres_air_database):
        """Test repo_url computed property."""
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        assert config.repo_url == "https://github.com/test_owner/test_repo"

    def test_graphmcp_compatibility(self, postgres_air_database):
        """Test compatibility with GraphMCP patterns."""
        # Test that dataclass can be used with asdict (GraphMCP pattern)
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        dict_result = asdict(config)
        
        assert isinstance(dict_result, dict)
        assert dict_result["database_name"] == postgres_air_database


@pytest.mark.unit
class TestWorkflowExecutionResult:
    """Test WorkflowExecutionResult data model."""

    def test_basic_creation(self, test_workflow_id, postgres_air_database):
        """Test basic result creation."""
        result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=True,
            duration_seconds=10.5,
            steps_completed=5,
            total_steps=5,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
        )
        
        assert result.workflow_id == test_workflow_id
        assert result.database_name == postgres_air_database
        assert result.success is True
        assert result.duration_seconds == 10.5
        assert result.steps_completed == 5
        assert result.total_steps == 5

    def test_manager_integration_fields(self, test_workflow_id, postgres_air_database):
        """Test Manager-specific fields."""
        execution_context = {
            "tenant_id": "test_tenant",
            "user_id": "test_user",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        
        result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=True,
            duration_seconds=5.0,
            steps_completed=3,
            total_steps=3,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
            execution_context=execution_context,
        )
        
        assert result.execution_context == execution_context
        assert result.execution_context["tenant_id"] == "test_tenant"

    def test_to_dict_conversion(self, sample_workflow_execution_result):
        """Test conversion to dictionary."""
        result = sample_workflow_execution_result.to_dict()
        
        assert isinstance(result, dict)
        assert result["workflow_id"] == sample_workflow_execution_result.workflow_id
        assert result["success"] == sample_workflow_execution_result.success
        assert result["duration_seconds"] == sample_workflow_execution_result.duration_seconds

    def test_success_rate_calculation(self, test_workflow_id, postgres_air_database):
        """Test success rate calculation."""
        # Test successful execution
        success_result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=True,
            duration_seconds=10.0,
            steps_completed=5,
            total_steps=5,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
        )
        
        assert success_result.success_rate == 100.0

        # Test partial execution
        partial_result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=False,
            duration_seconds=5.0,
            steps_completed=3,
            total_steps=5,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
        )
        
        assert partial_result.success_rate == 60.0

        # Test zero steps
        zero_result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=False,
            duration_seconds=1.0,
            steps_completed=0,
            total_steps=0,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
        )
        
        assert zero_result.success_rate == 0.0


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult enum."""

    def test_enum_values(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.PASSED.value == "passed"
        assert ValidationResult.WARNING.value == "warning"
        assert ValidationResult.FAILED.value == "failed"

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert ValidationResult.PASSED != ValidationResult.FAILED
        assert ValidationResult.WARNING != ValidationResult.PASSED


@pytest.mark.unit
class TestQualityAssuranceResult:
    """Test QualityAssuranceResult data model."""

    def test_basic_creation(self):
        """Test basic QA result creation."""
        result = QualityAssuranceResult(
            overall_status=ValidationResult.PASSED,
            quality_score=85.5,
            gates_passed=4,
            total_gates=5,
            gate_results=[],
            recommendations=[],
        )
        
        assert result.overall_status == ValidationResult.PASSED
        assert result.quality_score == 85.5
        assert result.gates_passed == 4
        assert result.total_gates == 5

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        result = QualityAssuranceResult(
            overall_status=ValidationResult.WARNING,
            quality_score=70.0,
            gates_passed=2,
            total_gates=3,
            gate_results=[{"gate": "test"}],
            recommendations=["Review quality"],
            details={"test": "data"},
        )
        
        dict_result = result.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result["overall_status"] == "warning"
        assert dict_result["quality_score"] == 70.0
        assert dict_result["gate_results"] == [{"gate": "test"}]


@pytest.mark.unit
class TestFileProcessingResult:
    """Test FileProcessingResult data model."""

    def test_basic_creation(self):
        """Test basic file processing result creation."""
        result = FileProcessingResult(
            file_path="test/file.py",
            strategy="code",
            success=True,
            modifications=[],
            confidence_score=0.9,
        )
        
        assert result.file_path == "test/file.py"
        assert result.strategy == "code"
        assert result.success is True
        assert result.confidence_score == 0.9

    def test_with_modifications(self):
        """Test result with modifications."""
        modifications = [
            {"line": 10, "change": "removed", "content": "old code"},
            {"line": 15, "change": "added", "content": "new code"},
        ]
        
        result = FileProcessingResult(
            file_path="test/file.py",
            strategy="code",
            success=True,
            modifications=modifications,
            confidence_score=0.8,
            metadata={"processor": "test"},
        )
        
        assert len(result.modifications) == 2
        assert result.metadata["processor"] == "test"

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        result = FileProcessingResult(
            file_path="test/file.py",
            strategy="documentation",
            success=False,
            modifications=[],
            confidence_score=0.5,
            error_message="Test error",
        )
        
        dict_result = result.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result["file_path"] == "test/file.py"
        assert dict_result["success"] is False
        assert dict_result["error_message"] == "Test error"


@pytest.mark.unit
class TestDatabaseDecommissionRequest:
    """Test DatabaseDecommissionRequest Pydantic model."""

    def test_basic_creation(self, postgres_air_database):
        """Test basic request creation."""
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        assert request.database_name == postgres_air_database
        assert request.repo_owner == "test_owner"
        assert request.repo_name == "test_repo"
        assert request.tenant_id is None
        assert request.async_execution is False

    def test_manager_integration_fields(self, postgres_air_database, test_tenant_id):
        """Test Manager-specific fields."""
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
            async_execution=True,
        )
        
        assert request.tenant_id == test_tenant_id
        assert request.user_id == "test_user"
        assert request.async_execution is True

    def test_pydantic_validation(self):
        """Test Pydantic validation."""
        # Test validation with missing required fields
        with pytest.raises(ValueError):
            DatabaseDecommissionRequest()

        # Test validation with invalid types
        with pytest.raises(ValueError):
            DatabaseDecommissionRequest(
                database_name=123,  # Should be string
                repo_owner="test",
                repo_name="test",
            )

    def test_json_serialization(self, postgres_air_database, test_tenant_id):
        """Test JSON serialization."""
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
        )
        
        json_str = request.model_dump_json()
        assert isinstance(json_str, str)
        assert postgres_air_database in json_str
        assert test_tenant_id in json_str


@pytest.mark.unit
class TestDatabaseDecommissionResponse:
    """Test DatabaseDecommissionResponse Pydantic model."""

    def test_basic_creation(self, test_workflow_id):
        """Test basic response creation."""
        response = DatabaseDecommissionResponse(
            workflow_id=test_workflow_id,
            status="completed",
            message="Workflow completed successfully",
        )
        
        assert response.workflow_id == test_workflow_id
        assert response.status == "completed"
        assert response.message == "Workflow completed successfully"
        assert response.result is None

    def test_with_result(self, test_workflow_id, sample_workflow_execution_result):
        """Test response with execution result."""
        response = DatabaseDecommissionResponse(
            workflow_id=test_workflow_id,
            status="completed",
            message="Success",
            result=sample_workflow_execution_result.to_dict(),
        )
        
        assert response.result is not None
        assert isinstance(response.result, dict)
        assert response.result["workflow_id"] == sample_workflow_execution_result.workflow_id

    def test_json_serialization(self, test_workflow_id):
        """Test JSON serialization."""
        response = DatabaseDecommissionResponse(
            workflow_id=test_workflow_id,
            status="running",
            message="Workflow in progress",
        )
        
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        assert test_workflow_id in json_str
        assert "running" in json_str


@pytest.mark.unit
@pytest.mark.manager
class TestModelManagerIntegration:
    """Test Manager-specific model integration features."""

    def test_workflow_config_tenant_awareness(self, postgres_air_database, test_tenant_id):
        """Test tenant-aware workflow configuration."""
        config = WorkflowConfig(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        # Test tenant context is preserved
        assert config.tenant_id == test_tenant_id
        assert config.user_id == "test_user"
        
        # Test conversion preserves tenant data
        dict_result = config.to_dict()
        assert dict_result["tenant_id"] == test_tenant_id
        
        # Test reconstruction preserves tenant data
        reconstructed = WorkflowConfig.from_dict(dict_result)
        assert reconstructed.tenant_id == test_tenant_id

    def test_execution_result_manager_context(self, test_workflow_id, postgres_air_database):
        """Test execution result with Manager context."""
        execution_context = {
            "tenant_id": "test_tenant",
            "user_id": "test_user",
            "manager_version": "1.0.0",
            "api_endpoint": "http://localhost:9123",
        }
        
        result = WorkflowExecutionResult(
            workflow_id=test_workflow_id,
            database_name=postgres_air_database,
            success=True,
            duration_seconds=5.0,
            steps_completed=3,
            total_steps=3,
            discovery_result={},
            validation_results=[],
            final_recommendations=[],
            execution_context=execution_context,
        )
        
        # Test Manager context is preserved
        assert result.execution_context["tenant_id"] == "test_tenant"
        assert result.execution_context["manager_version"] == "1.0.0"
        
        # Test serialization preserves Manager context
        dict_result = result.to_dict()
        assert dict_result["execution_context"]["tenant_id"] == "test_tenant"

    def test_request_response_compatibility(self, postgres_air_database, test_tenant_id):
        """Test compatibility between request and response models."""
        # Create request
        request = DatabaseDecommissionRequest(
            database_name=postgres_air_database,
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        # Create matching response
        response = DatabaseDecommissionResponse(
            workflow_id="test_workflow",
            status="completed",
            message="Success",
            result={
                "database_name": request.database_name,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
            },
        )
        
        # Test compatibility
        assert response.result["database_name"] == request.database_name
        assert response.result["tenant_id"] == request.tenant_id
        assert response.result["user_id"] == request.user_id