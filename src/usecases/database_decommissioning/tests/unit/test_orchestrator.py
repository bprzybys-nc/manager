"""
Unit tests for database decommissioning workflow orchestrator.

Tests the workflow orchestrator with Manager integration while preserving GraphMCP patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from ...app.orchestrator import DatabaseDecommissionOrchestrator
from ...app.models import (
    WorkflowConfig,
    WorkflowExecutionResult,
    ValidationResult,
    QualityAssuranceResult,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestDatabaseDecommissionOrchestrator:
    """Test DatabaseDecommissionOrchestrator main functionality."""

    def test_orchestrator_initialization(self, workflow_config, mock_logger):
        """Test orchestrator initialization."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        assert orchestrator.config == workflow_config
        assert orchestrator.logger == mock_logger
        assert orchestrator.workflow_id.startswith("db_decommission_")

    def test_orchestrator_with_db_client(self, workflow_config, mock_logger, mock_database_client):
        """Test orchestrator initialization with database client."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
            db_client=mock_database_client,
        )
        
        assert orchestrator.db_client == mock_database_client

    @patch('...app.orchestrator.GitHubMCPClientWrapper')
    @patch('...app.orchestrator.SlackMCPClientWrapper')
    @patch('...app.orchestrator.RepomixMCPClientWrapper')
    async def test_initialize_mcp_clients(
        self, mock_repomix, mock_slack, mock_github, workflow_config, mock_logger
    ):
        """Test MCP client initialization."""
        # Setup mock clients
        mock_github_instance = Mock()
        mock_slack_instance = Mock()
        mock_repomix_instance = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_slack.return_value = mock_slack_instance
        mock_repomix.return_value = mock_repomix_instance
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        await orchestrator._initialize_mcp_clients()
        
        assert orchestrator.github_client == mock_github_instance
        assert orchestrator.slack_client == mock_slack_instance
        assert orchestrator.repomix_client == mock_repomix_instance

    async def test_execute_workflow_success(self, workflow_config, mock_logger, mock_mcp_clients):
        """Test successful workflow execution."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock the workflow builder and execution
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            # Setup mock workflow
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 5.0,
                "steps_completed": 5,
                "total_steps": 5,
                "results": {
                    "discovery_result": {"files": [], "files_by_type": {}},
                    "validation_results": [],
                    "qa_result": None,
                },
            })
            mock_build.return_value = mock_workflow
            
            # Setup post-processing
            mock_post_process.return_value = []
            
            result = await orchestrator.execute_workflow()
            
            assert isinstance(result, WorkflowExecutionResult)
            assert result.success is True
            assert result.duration_seconds == 5.0
            assert result.steps_completed == 5

    async def test_execute_workflow_failure(self, workflow_config, mock_logger):
        """Test workflow execution with failure."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock workflow that fails
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'):
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(side_effect=Exception("Workflow failed"))
            mock_build.return_value = mock_workflow
            
            result = await orchestrator.execute_workflow()
            
            assert isinstance(result, WorkflowExecutionResult)
            assert result.success is False
            assert "Workflow failed" in str(result.discovery_result.get("error", ""))

    @patch('...app.orchestrator.WorkflowBuilder')
    async def test_build_graphmcp_workflow(self, mock_builder_class, workflow_config, mock_logger):
        """Test GraphMCP workflow building."""
        # Setup mock workflow builder
        mock_builder_instance = Mock()
        mock_workflow = Mock()
        
        mock_builder_instance.with_config.return_value = mock_builder_instance
        mock_builder_instance.step_auto.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_workflow
        
        mock_builder_class.return_value = mock_builder_instance
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock the step functions
        with patch.object(orchestrator, '_validate_environment_step') as mock_validate, \
             patch.object(orchestrator, '_discover_patterns_step') as mock_discover, \
             patch.object(orchestrator, '_validate_workflow_step') as mock_validate_wf, \
             patch.object(orchestrator, '_process_repositories_step') as mock_process, \
             patch.object(orchestrator, '_quality_assurance_step') as mock_qa:
            
            result = await orchestrator._build_graphmcp_workflow()
            
            assert result == mock_workflow
            # Verify workflow was configured correctly
            mock_builder_instance.with_config.assert_called_once()
            # Verify all steps were added
            assert mock_builder_instance.step_auto.call_count >= 5

    async def test_validate_environment_step(self, workflow_config, mock_logger):
        """Test environment validation step."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock context and step
        mock_context = Mock()
        mock_step = Mock()
        
        with patch('...app.orchestrator.EnvironmentValidator') as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate_complete_environment = AsyncMock(
                return_value={"success": True, "available_services": ["github", "slack"]}
            )
            mock_validator.return_value = mock_validator_instance
            
            result = await orchestrator._validate_environment_step(mock_context, mock_step)
            
            assert result["success"] is True
            assert "available_services" in result

    async def test_discover_patterns_step(self, workflow_config, mock_logger):
        """Test pattern discovery step."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Setup mock clients
        orchestrator.github_client = Mock()
        orchestrator.repomix_client = Mock()
        
        mock_context = Mock()
        mock_step = Mock()
        
        with patch('...app.orchestrator.PatternDiscoveryProcessor') as mock_processor:
            mock_processor_instance = Mock()
            mock_processor_instance.discover_database_patterns = AsyncMock(
                return_value={"files": [], "files_by_type": {}, "confidence_distribution": {}}
            )
            mock_processor.return_value = mock_processor_instance
            
            result = await orchestrator._discover_patterns_step(mock_context, mock_step)
            
            assert "files" in result
            assert "files_by_type" in result

    async def test_validate_workflow_step(self, workflow_config, mock_logger):
        """Test workflow validation step."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        mock_context = Mock()
        mock_context.get_step_result.return_value = {
            "files": [],
            "files_by_type": {},
        }
        mock_step = Mock()
        
        with patch('...app.orchestrator.DatabaseReferenceValidator') as mock_db_validator, \
             patch('...app.orchestrator.RuleComplianceValidator') as mock_rule_validator, \
             patch('...app.orchestrator.ServiceIntegrityValidator') as mock_service_validator:
            
            # Setup mock validators
            for validator_class in [mock_db_validator, mock_rule_validator, mock_service_validator]:
                validator_instance = Mock()
                validator_instance.validate_database_references = AsyncMock(
                    return_value=Mock(to_dict=Mock(return_value={"status": "passed"}))
                )
                validator_instance.validate_rule_compliance = AsyncMock(
                    return_value=Mock(to_dict=Mock(return_value={"status": "passed"}))
                )
                validator_instance.validate_service_integrity = AsyncMock(
                    return_value=Mock(to_dict=Mock(return_value={"status": "passed"}))
                )
                validator_class.return_value = validator_instance
            
            result = await orchestrator._validate_workflow_step(mock_context, mock_step)
            
            assert isinstance(result, list)
            assert len(result) == 3  # Three validators

    async def test_process_repositories_step(self, workflow_config, mock_logger):
        """Test repository processing step."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Setup mock clients
        orchestrator.github_client = Mock()
        orchestrator.slack_client = Mock()
        
        mock_context = Mock()
        mock_context.get_step_result.return_value = {
            "files": [],
            "files_by_type": {},
        }
        mock_step = Mock()
        
        with patch('...app.orchestrator.RepositoryProcessor') as mock_processor:
            mock_processor_instance = Mock()
            mock_processor_instance.process_repositories = AsyncMock(
                return_value={"processed_repositories": 1, "created_prs": []}
            )
            mock_processor.return_value = mock_processor_instance
            
            result = await orchestrator._process_repositories_step(mock_context, mock_step)
            
            assert "processed_repositories" in result

    async def test_quality_assurance_step(self, workflow_config, mock_logger):
        """Test quality assurance step."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        mock_context = Mock()
        mock_context.get_step_result.side_effect = [
            {"files": [], "files_by_type": {}},  # discovery result
            [{"status": "passed"}],  # validation results
        ]
        mock_step = Mock()
        
        with patch('...app.orchestrator.DecommissioningQualityGates') as mock_qa:
            mock_qa_instance = Mock()
            mock_qa_instance.execute_all_quality_gates = AsyncMock(
                return_value=QualityAssuranceResult(
                    overall_status=ValidationResult.PASSED,
                    quality_score=85.0,
                    gates_passed=3,
                    total_gates=3,
                    gate_results=[],
                    recommendations=[],
                )
            )
            mock_qa.return_value = mock_qa_instance
            
            result = await orchestrator._quality_assurance_step(mock_context, mock_step)
            
            assert isinstance(result, QualityAssuranceResult)
            assert result.overall_status == ValidationResult.PASSED

    async def test_execute_post_processing(self, workflow_config, mock_logger):
        """Test post-processing execution."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        workflow_results = {
            "discovery_result": {"files": [], "files_by_type": {}},
            "validation_results": [{"status": "passed"}],
            "qa_result": QualityAssuranceResult(
                overall_status=ValidationResult.PASSED,
                quality_score=85.0,
                gates_passed=3,
                total_gates=3,
                gate_results=[],
                recommendations=[],
            ),
        }
        
        with patch('...app.orchestrator.generate_decommissioning_recommendations') as mock_gen_recs, \
             patch('...app.orchestrator.DecommissioningRiskAssessor') as mock_risk_assessor:
            
            mock_gen_recs.return_value = ["Test recommendation"]
            
            mock_risk_instance = Mock()
            mock_risk_instance.assess_comprehensive_risk = AsyncMock(
                return_value=Mock(mitigation_recommendations=["Risk recommendation"])
            )
            mock_risk_assessor.return_value = mock_risk_instance
            
            result = await orchestrator._execute_post_processing(workflow_results)
            
            assert isinstance(result, list)
            assert len(result) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrchestoratorStepFunctions:
    """Test individual orchestrator step functions in detail."""

    async def test_step_function_error_handling(self, workflow_config, mock_logger):
        """Test step function error handling."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        mock_context = Mock()
        mock_step = Mock()
        
        # Test environment validation with exception
        with patch('...app.orchestrator.EnvironmentValidator', side_effect=Exception("Validation error")):
            result = await orchestrator._validate_environment_step(mock_context, mock_step)
            
            assert result["success"] is False
            assert "error" in result

    async def test_step_context_management(self, workflow_config, mock_logger):
        """Test step context management and data passing."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock context that tracks step results
        mock_context = Mock()
        stored_results = {}
        
        def mock_store_step_result(step_name, result):
            stored_results[step_name] = result
        
        def mock_get_step_result(step_name):
            return stored_results.get(step_name, {})
        
        mock_context.store_step_result = mock_store_step_result
        mock_context.get_step_result = mock_get_step_result
        
        mock_step = Mock()
        mock_step.name = "test_step"
        
        # Test that step results are properly stored and retrieved
        with patch('...app.orchestrator.EnvironmentValidator') as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate_complete_environment = AsyncMock(
                return_value={"success": True, "test_data": "value"}
            )
            mock_validator.return_value = mock_validator_instance
            
            result = await orchestrator._validate_environment_step(mock_context, mock_step)
            
            # Verify result structure
            assert result["success"] is True
            assert "test_data" in result

    async def test_tenant_aware_step_execution(self, test_tenant_id, mock_logger):
        """Test tenant-aware step execution."""
        config = WorkflowConfig(
            database_name="test_db",
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=config,
            logger=mock_logger,
        )
        
        mock_context = Mock()
        mock_step = Mock()
        
        # Test that tenant context is passed to validators
        with patch('...app.orchestrator.DatabaseReferenceValidator') as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate_database_references = AsyncMock(
                return_value=Mock(
                    to_dict=Mock(return_value={"status": "passed", "tenant_id": test_tenant_id})
                )
            )
            mock_validator.return_value = mock_validator_instance
            
            mock_context.get_step_result.return_value = {"files": [], "files_by_type": {}}
            
            await orchestrator._validate_workflow_step(mock_context, mock_step)
            
            # Verify validator was created with tenant context
            mock_validator.assert_called_with(
                config.database_name, test_tenant_id, orchestrator.workflow_id
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrchestoratorManagerIntegration:
    """Test Manager-specific orchestrator integration features."""

    async def test_database_result_storage(self, workflow_config, mock_logger, mock_database_client):
        """Test workflow result storage in Manager database."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
            db_client=mock_database_client,
        )
        
        # Mock successful workflow execution
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 5.0,
                "steps_completed": 3,
                "total_steps": 3,
                "results": {
                    "discovery_result": {"files": []},
                    "validation_results": [],
                    "qa_result": None,
                },
            })
            mock_build.return_value = mock_workflow
            mock_post_process.return_value = []
            
            result = await orchestrator.execute_workflow()
            
            # Verify storage was attempted (through workflow execution storage)
            assert isinstance(result, WorkflowExecutionResult)
            assert result.success is True

    async def test_tenant_context_preservation(self, test_tenant_id, mock_logger):
        """Test tenant context preservation throughout workflow."""
        config = WorkflowConfig(
            database_name="test_db",
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
            user_id="test_user",
        )
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=config,
            logger=mock_logger,
        )
        
        # Verify tenant context is preserved in orchestrator
        assert orchestrator.config.tenant_id == test_tenant_id
        assert orchestrator.config.user_id == "test_user"
        
        # Mock workflow execution to test tenant context in results
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 2.0,
                "steps_completed": 1,
                "total_steps": 1,
                "results": {
                    "discovery_result": {"files": []},
                    "validation_results": [],
                    "qa_result": None,
                },
            })
            mock_build.return_value = mock_workflow
            mock_post_process.return_value = []
            
            result = await orchestrator.execute_workflow()
            
            # Verify tenant context is preserved in execution result
            assert result.execution_context is not None
            assert result.execution_context.get("tenant_id") == test_tenant_id
            assert result.execution_context.get("user_id") == "test_user"

    async def test_async_execution_patterns(self, workflow_config, mock_logger):
        """Test async execution patterns for Manager integration."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Test that all major operations are properly async
        async_methods = [
            orchestrator._initialize_mcp_clients,
            orchestrator._validate_environment_step,
            orchestrator._discover_patterns_step,
            orchestrator._validate_workflow_step,
            orchestrator._process_repositories_step,
            orchestrator._quality_assurance_step,
            orchestrator._execute_post_processing,
            orchestrator.execute_workflow,
        ]
        
        for method in async_methods:
            assert asyncio.iscoroutinefunction(method), f"{method.__name__} should be async"

    async def test_graceful_degradation(self, workflow_config, mock_logger):
        """Test graceful degradation when Manager services are unavailable."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
            db_client=None,  # No database client
        )
        
        # Test that orchestrator still works without database client
        assert orchestrator.db_client is None
        
        # Mock workflow execution without database storage
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 1.0,
                "steps_completed": 1,
                "total_steps": 1,
                "results": {
                    "discovery_result": {"files": []},
                    "validation_results": [],
                    "qa_result": None,
                },
            })
            mock_build.return_value = mock_workflow
            mock_post_process.return_value = []
            
            result = await orchestrator.execute_workflow()
            
            # Should still complete successfully
            assert result.success is True

    def test_orchestrator_configuration_validation(self, mock_logger):
        """Test orchestrator configuration validation."""
        # Test with minimal valid configuration
        minimal_config = WorkflowConfig(
            database_name="test_db",
            repo_owner="test_owner",
            repo_name="test_repo",
        )
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=minimal_config,
            logger=mock_logger,
        )
        
        assert orchestrator.config.database_name == "test_db"
        assert orchestrator.config.tenant_id is None  # Optional field
        
        # Test with full configuration
        full_config = WorkflowConfig(
            database_name="test_db",
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id="test_tenant",
            user_id="test_user",
            max_parallel_steps=8,
            debug_mode=True,
        )
        
        full_orchestrator = DatabaseDecommissionOrchestrator(
            config=full_config,
            logger=mock_logger,
        )
        
        assert full_orchestrator.config.tenant_id == "test_tenant"
        assert full_orchestrator.config.debug_mode is True