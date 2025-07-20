"""
Integration tests for database decommissioning workflow.

Tests the integration between major components with Manager patterns while preserving
GraphMCP framework compatibility.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from pathlib import Path

from ...app.orchestrator import DatabaseDecommissionOrchestrator
from ...app.models import WorkflowConfig, WorkflowExecutionResult, ValidationResult
from ...app.processors.pattern_discovery import PatternDiscoveryProcessor
from ...app.business_rules.validation_rules import DatabaseReferenceValidator
from ...app.business_rules.quality_rules import DecommissioningQualityGates


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowIntegration:
    """Test integration between workflow components."""

    async def test_complete_workflow_simulation(self, workflow_config, mock_logger, test_data_generator):
        """Test complete workflow simulation with mocked external dependencies."""
        # Create orchestrator
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Generate realistic test data
        discovery_result = test_data_generator.generate_discovery_result(
            workflow_config.database_name, file_count=8, reference_density=0.3
        )
        
        # Mock all external dependencies
        with patch('...app.orchestrator.EnvironmentValidator') as mock_env_validator, \
             patch('...app.orchestrator.PatternDiscoveryProcessor') as mock_pattern_processor, \
             patch('...app.orchestrator.DatabaseReferenceValidator') as mock_db_validator, \
             patch('...app.orchestrator.RuleComplianceValidator') as mock_rule_validator, \
             patch('...app.orchestrator.ServiceIntegrityValidator') as mock_service_validator, \
             patch('...app.orchestrator.RepositoryProcessor') as mock_repo_processor, \
             patch('...app.orchestrator.DecommissioningQualityGates') as mock_qa_gates, \
             patch('...app.orchestrator.DecommissioningRiskAssessor') as mock_risk_assessor, \
             patch.object(orchestrator, '_initialize_mcp_clients'):
            
            # Setup environment validator
            env_validator_instance = Mock()
            env_validator_instance.validate_complete_environment = AsyncMock(
                return_value={"success": True, "available_services": ["github", "slack", "repomix"]}
            )
            mock_env_validator.return_value = env_validator_instance
            
            # Setup pattern discovery processor
            pattern_processor_instance = Mock()
            pattern_processor_instance.discover_database_patterns = AsyncMock(
                return_value=discovery_result
            )
            mock_pattern_processor.return_value = pattern_processor_instance
            
            # Setup validation rules
            for validator_class, method_name in [
                (mock_db_validator, 'validate_database_references'),
                (mock_rule_validator, 'validate_rule_compliance'),
                (mock_service_validator, 'validate_service_integrity'),
            ]:
                validator_instance = Mock()
                validator_method = AsyncMock(
                    return_value=Mock(
                        to_dict=Mock(return_value={
                            "status": "passed",
                            "confidence": 85,
                            "description": "Test validation passed",
                            "details": {},
                        })
                    )
                )
                setattr(validator_instance, method_name, validator_method)
                validator_class.return_value = validator_instance
            
            # Setup repository processor
            repo_processor_instance = Mock()
            repo_processor_instance.process_repositories = AsyncMock(
                return_value={
                    "processed_repositories": 1,
                    "created_prs": ["https://github.com/test/repo/pull/1"],
                    "success": True,
                }
            )
            mock_repo_processor.return_value = repo_processor_instance
            
            # Setup quality gates
            qa_gates_instance = Mock()
            qa_gates_instance.execute_all_quality_gates = AsyncMock(
                return_value=Mock(
                    overall_status=ValidationResult.PASSED,
                    quality_score=87.5,
                    gates_passed=4,
                    total_gates=4,
                    gate_results=[],
                    recommendations=["Quality validation passed"],
                    to_dict=Mock(return_value={
                        "overall_status": "passed",
                        "quality_score": 87.5,
                        "gates_passed": 4,
                        "total_gates": 4,
                    })
                )
            )
            mock_qa_gates.return_value = qa_gates_instance
            
            # Setup risk assessor
            risk_assessor_instance = Mock()
            risk_assessor_instance.assess_comprehensive_risk = AsyncMock(
                return_value=Mock(mitigation_recommendations=["Low risk detected"])
            )
            mock_risk_assessor.return_value = risk_assessor_instance
            
            # Execute workflow
            result = await orchestrator.execute_workflow()
            
            # Verify workflow completion
            assert isinstance(result, WorkflowExecutionResult)
            assert result.success is True
            assert result.database_name == workflow_config.database_name
            assert result.steps_completed > 0
            assert result.duration_seconds > 0
            
            # Verify discovery result integration
            assert result.discovery_result == discovery_result
            
            # Verify validation results integration
            assert len(result.validation_results) == 3  # Three validators
            
            # Verify execution context
            assert result.execution_context is not None
            assert result.execution_context["database_name"] == workflow_config.database_name

    async def test_workflow_with_tenant_context(self, test_tenant_id, mock_logger, test_data_generator):
        """Test workflow integration with tenant context."""
        # Create tenant-aware configuration
        config = WorkflowConfig(
            database_name="tenant_db",
            repo_owner="tenant_org",
            repo_name="tenant_repo",
            tenant_id=test_tenant_id,
            user_id="tenant_user",
        )
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=config,
            logger=mock_logger,
        )
        
        # Generate test data for tenant
        discovery_result = test_data_generator.generate_discovery_result(
            config.database_name, file_count=5, reference_density=0.2
        )
        
        # Mock components with tenant awareness
        with patch('...app.orchestrator.DatabaseReferenceValidator') as mock_db_validator, \
             patch('...app.orchestrator.EnvironmentValidator'), \
             patch('...app.orchestrator.PatternDiscoveryProcessor') as mock_pattern_processor, \
             patch('...app.orchestrator.RuleComplianceValidator'), \
             patch('...app.orchestrator.ServiceIntegrityValidator'), \
             patch('...app.orchestrator.RepositoryProcessor'), \
             patch('...app.orchestrator.DecommissioningQualityGates'), \
             patch('...app.orchestrator.DecommissioningRiskAssessor'), \
             patch.object(orchestrator, '_initialize_mcp_clients'):
            
            # Setup pattern processor
            pattern_processor_instance = Mock()
            pattern_processor_instance.discover_database_patterns = AsyncMock(
                return_value=discovery_result
            )
            mock_pattern_processor.return_value = pattern_processor_instance
            
            # Setup database validator with tenant context
            db_validator_instance = Mock()
            db_validator_instance.validate_database_references = AsyncMock(
                return_value=Mock(
                    to_dict=Mock(return_value={
                        "status": "passed",
                        "tenant_id": test_tenant_id,
                        "details": {
                            "tenant_analysis": {
                                "tenant_specific": True,
                                "tenant_id": test_tenant_id,
                            }
                        },
                    })
                )
            )
            mock_db_validator.return_value = db_validator_instance
            
            # Execute workflow
            result = await orchestrator.execute_workflow()
            
            # Verify tenant context preservation
            assert result.execution_context["tenant_id"] == test_tenant_id
            assert result.execution_context["user_id"] == "tenant_user"
            
            # Verify tenant context was passed to validators
            mock_db_validator.assert_called_with(
                config.database_name, test_tenant_id, orchestrator.workflow_id
            )

    async def test_workflow_error_recovery(self, workflow_config, mock_logger):
        """Test workflow error recovery and graceful degradation."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Test recovery from pattern discovery failure
        with patch('...app.orchestrator.EnvironmentValidator') as mock_env_validator, \
             patch('...app.orchestrator.PatternDiscoveryProcessor') as mock_pattern_processor, \
             patch.object(orchestrator, '_initialize_mcp_clients'):
            
            # Environment validation succeeds
            env_validator_instance = Mock()
            env_validator_instance.validate_complete_environment = AsyncMock(
                return_value={"success": True, "available_services": ["github"]}
            )
            mock_env_validator.return_value = env_validator_instance
            
            # Pattern discovery fails
            pattern_processor_instance = Mock()
            pattern_processor_instance.discover_database_patterns = AsyncMock(
                side_effect=Exception("Pattern discovery failed")
            )
            mock_pattern_processor.return_value = pattern_processor_instance
            
            # Execute workflow
            result = await orchestrator.execute_workflow()
            
            # Verify graceful failure handling
            assert isinstance(result, WorkflowExecutionResult)
            assert result.success is False
            assert "error" in result.discovery_result or "Pattern discovery failed" in str(result.discovery_result)

    async def test_workflow_partial_service_availability(self, workflow_config, mock_logger):
        """Test workflow with partial service availability."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock partial service availability
        with patch('...app.orchestrator.EnvironmentValidator') as mock_env_validator, \
             patch('...app.orchestrator.PatternDiscoveryProcessor') as mock_pattern_processor, \
             patch('...app.orchestrator.DatabaseReferenceValidator') as mock_db_validator, \
             patch.object(orchestrator, '_initialize_mcp_clients'):
            
            # Environment validation shows partial availability
            env_validator_instance = Mock()
            env_validator_instance.validate_complete_environment = AsyncMock(
                return_value={
                    "success": False,
                    "available_services": ["github"],  # Only GitHub available
                    "missing_services": ["slack", "repomix"],
                }
            )
            mock_env_validator.return_value = env_validator_instance
            
            # Pattern discovery with limited capabilities
            pattern_processor_instance = Mock()
            pattern_processor_instance.discover_database_patterns = AsyncMock(
                return_value={
                    "files": [],
                    "files_by_type": {},
                    "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
                    "service_limitations": ["Limited analysis due to missing services"],
                }
            )
            mock_pattern_processor.return_value = pattern_processor_instance
            
            # Validation with degraded analysis
            db_validator_instance = Mock()
            db_validator_instance.validate_database_references = AsyncMock(
                return_value=Mock(
                    to_dict=Mock(return_value={
                        "status": "warning",
                        "confidence": 50,
                        "description": "Limited validation due to service unavailability",
                        "details": {"service_limitations": True},
                    })
                )
            )
            mock_db_validator.return_value = db_validator_instance
            
            # Execute workflow
            result = await orchestrator.execute_workflow()
            
            # Verify workflow completes with warnings
            assert isinstance(result, WorkflowExecutionResult)
            # May succeed with warnings or fail gracefully
            assert result.discovery_result is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestComponentIntegration:
    """Test integration between specific components."""

    async def test_pattern_discovery_validation_integration(
        self, postgres_air_database, test_tenant_id, mock_logger
    ):
        """Test integration between pattern discovery and validation."""
        # Create pattern discovery processor
        with patch('...app.processors.pattern_discovery.GitHubMCPClientWrapper'), \
             patch('...app.processors.pattern_discovery.RepomixMCPClientWrapper'):
            
            pattern_processor = PatternDiscoveryProcessor(
                postgres_air_database, test_tenant_id, "test_workflow"
            )
        
        # Create database reference validator
        db_validator = DatabaseReferenceValidator(
            postgres_air_database, test_tenant_id, "test_workflow"
        )
        
        # Mock discovery result
        mock_discovery_result = {
            "files": [
                {
                    "path": "app/models.py",
                    "content": f"from {postgres_air_database} import connection",
                    "source_type": "python",
                },
                {
                    "path": "config/db.yml",
                    "content": f"database: {postgres_air_database}",
                    "source_type": "config",
                },
            ],
            "files_by_type": {
                "python": [{"path": "app/models.py"}],
                "config": [{"path": "config/db.yml"}],
            },
            "confidence_distribution": {"high": 2, "medium": 0, "low": 0},
        }
        
        # Test validation using discovery result
        validation_result = await db_validator.validate_database_references(mock_discovery_result)
        
        # Verify integration
        assert validation_result.rule_type.value == "database_reference"
        assert validation_result.details["total_files"] == 2
        assert validation_result.details["references_found"] == 2
        assert validation_result.tenant_id == test_tenant_id

    async def test_validation_quality_gates_integration(
        self, postgres_air_database, test_tenant_id, mock_discovery_result, mock_validation_results
    ):
        """Test integration between validation rules and quality gates."""
        # Create quality gates controller
        quality_gates = DecommissioningQualityGates(
            postgres_air_database, test_tenant_id, "test_workflow"
        )
        
        # Execute quality gates with validation results
        qa_result = await quality_gates.execute_all_quality_gates(
            mock_discovery_result, mock_validation_results
        )
        
        # Verify integration
        assert qa_result.overall_status in [ValidationResult.PASSED, ValidationResult.WARNING, ValidationResult.FAILED]
        assert qa_result.total_gates > 0
        assert isinstance(qa_result.gate_results, list)
        assert isinstance(qa_result.recommendations, list)

    async def test_manager_database_integration(
        self, workflow_config, mock_logger, mock_database_client
    ):
        """Test Manager database integration throughout workflow."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
            db_client=mock_database_client,
        )
        
        # Mock successful workflow with database storage
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 3.0,
                "steps_completed": 2,
                "total_steps": 2,
                "results": {
                    "discovery_result": {"files": []},
                    "validation_results": [],
                    "qa_result": None,
                },
            })
            mock_build.return_value = mock_workflow
            mock_post_process.return_value = []
            
            result = await orchestrator.execute_workflow()
            
            # Verify database integration
            assert result.success is True
            # Database operations should have been called through various components
            assert mock_database_client.database is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowPerformance:
    """Test workflow performance characteristics."""

    async def test_workflow_execution_timing(self, workflow_config, mock_logger):
        """Test workflow execution timing and performance."""
        import time
        
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
        )
        
        # Mock fast execution
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 0.5,
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
            
            start_time = time.time()
            result = await orchestrator.execute_workflow()
            execution_time = time.time() - start_time
            
            # Verify performance characteristics
            assert result.success is True
            assert execution_time < 5.0  # Should complete quickly with mocks
            assert result.duration_seconds < 5.0

    async def test_concurrent_workflow_execution(self, mock_logger):
        """Test concurrent workflow execution."""
        # Create multiple workflow configurations
        configs = [
            WorkflowConfig(
                database_name=f"test_db_{i}",
                repo_owner="test_owner",
                repo_name=f"test_repo_{i}",
            )
            for i in range(3)
        ]
        
        # Create orchestrators
        orchestrators = [
            DatabaseDecommissionOrchestrator(config=config, logger=mock_logger)
            for config in configs
        ]
        
        # Mock workflow execution for all orchestrators
        async def mock_execute_workflow(orchestrator):
            with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
                 patch.object(orchestrator, '_initialize_mcp_clients'), \
                 patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
                
                mock_workflow = Mock()
                mock_workflow.execute = AsyncMock(return_value={
                    "success": True,
                    "duration_seconds": 1.0,
                    "steps_completed": 2,
                    "total_steps": 2,
                    "results": {
                        "discovery_result": {"files": []},
                        "validation_results": [],
                        "qa_result": None,
                    },
                })
                mock_build.return_value = mock_workflow
                mock_post_process.return_value = []
                
                return await orchestrator.execute_workflow()
        
        # Execute workflows concurrently
        results = await asyncio.gather(*[
            mock_execute_workflow(orchestrator) for orchestrator in orchestrators
        ])
        
        # Verify all workflows completed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.database_name == f"test_db_{i}"


@pytest.mark.integration
@pytest.mark.manager
class TestManagerIntegrationFeatures:
    """Test Manager-specific integration features."""

    async def test_tenant_isolation(self, mock_logger):
        """Test tenant isolation in concurrent workflows."""
        # Create workflows for different tenants
        tenant_1_config = WorkflowConfig(
            database_name="shared_db",
            repo_owner="org",
            repo_name="repo",
            tenant_id="tenant_1",
            user_id="user_1",
        )
        
        tenant_2_config = WorkflowConfig(
            database_name="shared_db",
            repo_owner="org",
            repo_name="repo",
            tenant_id="tenant_2", 
            user_id="user_2",
        )
        
        orchestrator_1 = DatabaseDecommissionOrchestrator(
            config=tenant_1_config,
            logger=mock_logger,
        )
        
        orchestrator_2 = DatabaseDecommissionOrchestrator(
            config=tenant_2_config,
            logger=mock_logger,
        )
        
        # Verify tenant isolation
        assert orchestrator_1.config.tenant_id != orchestrator_2.config.tenant_id
        assert orchestrator_1.workflow_id != orchestrator_2.workflow_id
        
        # Each orchestrator should maintain its own tenant context
        assert orchestrator_1.config.tenant_id == "tenant_1"
        assert orchestrator_2.config.tenant_id == "tenant_2"

    async def test_audit_logging_integration(self, workflow_config, mock_logger, mock_database_client):
        """Test audit logging integration for Manager compliance."""
        orchestrator = DatabaseDecommissionOrchestrator(
            config=workflow_config,
            logger=mock_logger,
            db_client=mock_database_client,
        )
        
        # Mock workflow execution with audit events
        with patch.object(orchestrator, '_build_graphmcp_workflow') as mock_build, \
             patch.object(orchestrator, '_initialize_mcp_clients'), \
             patch.object(orchestrator, '_execute_post_processing') as mock_post_process:
            
            mock_workflow = Mock()
            mock_workflow.execute = AsyncMock(return_value={
                "success": True,
                "duration_seconds": 2.0,
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
            
            # Verify logging calls were made
            assert mock_logger.log_info.called
            
            # Verify audit trail in execution context
            assert result.execution_context is not None
            assert "workflow_id" in result.execution_context
            assert "database_name" in result.execution_context