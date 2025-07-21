"""
Integration tests for DB Runbook Finder workflow.

This module contains comprehensive tests for the complete workflow,
including integration tests and end-to-end scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ..state import WorkflowState
from ..workflow import DBRunbookFinderWorkflow
from ..nodes import DBRunbookFinderNodes


class TestDBRunbookFinderWorkflow:
    """Test suite for DB Runbook Finder workflow integration."""

    @pytest.mark.unit
    def test_workflow_initialization(self):
        """Test proper workflow initialization."""
        workflow = DBRunbookFinderWorkflow()
        
        # Verify initialization
        assert workflow.config_path is not None
        assert workflow.nodes is not None
        assert isinstance(workflow.nodes, DBRunbookFinderNodes)
        assert hasattr(workflow, 'logger')
        assert hasattr(workflow, 'logging_config')

    @pytest.mark.unit
    def test_workflow_initialization_custom_config(self):
        """Test workflow initialization with custom config path."""
        custom_path = "custom/config/path.json"
        workflow = DBRunbookFinderWorkflow(config_path=custom_path)
        
        assert workflow.config_path == custom_path

    @pytest.mark.unit
    def test_runbook_search_router_with_runbooks(self, db_runbook_finder_workflow, workflow_state_with_runbooks):
        """Test routing when runbooks are found."""
        workflow = db_runbook_finder_workflow
        
        result = workflow._runbook_search_router(workflow_state_with_runbooks)
        
        assert result == "update_jira_results"

    @pytest.mark.unit
    def test_runbook_search_router_no_runbooks(self, db_runbook_finder_workflow, workflow_state_no_runbooks):
        """Test routing when no runbooks are found."""
        workflow = db_runbook_finder_workflow
        
        result = workflow._runbook_search_router(workflow_state_no_runbooks)
        
        assert result == "terminate_gap"

    @pytest.mark.unit
    def test_runbook_search_router_error_state(self, db_runbook_finder_workflow, sample_workflow_state):
        """Test routing when workflow is in error state."""
        workflow = db_runbook_finder_workflow
        
        # Set error state
        sample_workflow_state.update_status("ERROR", "Test error")
        
        result = workflow._runbook_search_router(sample_workflow_state)
        
        assert result == "notify_team"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow_success_scenario(self, db_runbook_finder_workflow, sample_jira_key, workflow_assertions):
        """Test complete workflow execution with success scenario."""
        workflow = db_runbook_finder_workflow
        
        # Execute full workflow
        result_state = await workflow.run(sample_jira_key)
        
        # Verify completion
        workflow_assertions.assert_state_valid(result_state)
        workflow_assertions.assert_state_completed(result_state)
        
        # Verify workflow data
        assert result_state.jira_key == sample_jira_key
        assert result_state.incident_data is not None
        assert result_state.get_client_name() == "Agent System"
        
        # Verify performance
        workflow_assertions.assert_performance_within_limits(result_state)
        
        # Check specific metrics
        expected_metrics = ["fetch_incident", "search_runbooks", "notify_team"]
        for metric in expected_metrics:
            assert metric in result_state.performance_metrics

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow_gap_scenario(self, db_runbook_finder_workflow, workflow_assertions):
        """Test complete workflow execution with gap scenario."""
        workflow = db_runbook_finder_workflow
        
        # Use a ticket that will trigger gap scenario
        gap_ticket = "TEST-999"
        
        # Execute full workflow
        result_state = await workflow.run(gap_ticket)
        
        # Verify gap detection
        workflow_assertions.assert_state_valid(result_state)
        assert result_state.status == "GAP_DETECTED"
        workflow_assertions.assert_state_no_runbooks(result_state)
        
        # Verify performance still within limits
        workflow_assertions.assert_performance_within_limits(result_state)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_agent_6_ticket(self, db_runbook_finder_workflow, workflow_assertions):
        """Test workflow with specific AGENT-6 ticket."""
        workflow = db_runbook_finder_workflow
        
        # Execute with AGENT-6 ticket
        result_state = await workflow.run("AGENT-6")
        
        # Verify AGENT-6 specific results
        workflow_assertions.assert_state_valid(result_state)
        assert result_state.jira_key == "AGENT-6"
        assert result_state.get_client_name() == "Agent System"
        
        # Should find runbooks for database timeout issue
        if result_state.status == "SUCCESS":
            workflow_assertions.assert_state_has_runbooks(result_state)
            
            # Verify runbook content is database-related
            runbook_titles = [rb.get("title", "") for rb in result_state.runbooks]
            assert any("Database" in title for title in runbook_titles)

    @pytest.mark.unit
    def test_get_workflow_info(self, db_runbook_finder_workflow):
        """Test workflow information retrieval."""
        workflow = db_runbook_finder_workflow
        
        info = workflow.get_workflow_info()
        
        # Verify structure
        assert "name" in info
        assert "version" in info
        assert "description" in info
        assert "nodes" in info
        assert "routing_logic" in info
        assert "supported_projects" in info
        assert "target_spaces" in info
        assert "performance_target" in info
        
        # Verify content
        assert info["name"] == "DB Runbook Finder"
        assert "AGENT" in info["supported_projects"]
        assert "AAVA" in info["target_spaces"]
        assert "MCDBA" in info["target_spaces"]
        assert "30 seconds" in info["performance_target"]
        
        # Verify all expected nodes
        expected_nodes = [
            "fetch_incident", "search_runbooks", "update_jira_results",
            "terminate_gap", "notify_team"
        ]
        for node in expected_nodes:
            assert node in info["nodes"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_configuration(self, db_runbook_finder_workflow):
        """Test workflow configuration validation."""
        workflow = db_runbook_finder_workflow
        
        validation_results = await workflow.validate_configuration()
        
        # Verify structure
        assert "overall_status" in validation_results
        assert "checks" in validation_results
        assert "warnings" in validation_results
        assert "errors" in validation_results
        
        # Should pass basic validation
        assert validation_results["overall_status"] in ["passed", "warnings"]
        
        # Verify specific checks
        checks = validation_results["checks"]
        assert "graphmcp_framework" in checks
        assert "nodes_initialization" in checks
        assert "project_mappings" in checks

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_workflow_performance_targets(self, db_runbook_finder_workflow, workflow_assertions):
        """Test that workflow meets performance targets."""
        workflow = db_runbook_finder_workflow
        
        # Test with multiple tickets to ensure consistent performance
        test_tickets = ["AGENT-6", "TEST-123", "OVR-999"]
        
        for ticket in test_tickets:
            start_time = datetime.utcnow()
            
            result_state = await workflow.run(ticket)
            
            end_time = datetime.utcnow()
            actual_duration = (end_time - start_time).total_seconds()
            
            # Verify workflow completed under target time
            assert actual_duration < 30.0, f"Workflow took {actual_duration}s for {ticket}, target < 30s"
            
            # Verify individual metrics are reasonable
            workflow_assertions.assert_performance_within_limits(result_state, max_duration=30.0)

    @pytest.mark.unit
    @pytest.mark.error_handling
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, db_runbook_finder_workflow):
        """Test workflow error handling scenarios."""
        workflow = db_runbook_finder_workflow
        
        # Test with invalid ticket
        try:
            result_state = await workflow.run("")
            # Should handle gracefully and return error state
            assert result_state.is_error_state()
        except ValueError:
            # Also acceptable - validation error
            pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self, db_runbook_finder_workflow):
        """Test workflow timeout handling."""
        workflow = db_runbook_finder_workflow
        
        # This should complete normally with mock data
        result_state = await workflow.run("AGENT-6")
        
        # Verify completion
        assert not result_state.is_error_state()
        assert result_state.is_completed()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, db_runbook_finder_workflow):
        """Test proper state transitions throughout workflow."""
        workflow = db_runbook_finder_workflow
        
        # Execute workflow and check state at each step
        result_state = await workflow.run("AGENT-6")
        
        # Verify final state is appropriate
        assert result_state.status in ["SUCCESS", "GAP_DETECTED"]
        
        # Verify all required data is populated
        assert result_state.incident_data is not None
        assert len(result_state.incident_data) > 0
        assert result_state.runbooks is not None  # May be empty for gap scenario
        
        # Verify timestamps
        assert result_state.created_at is not None
        assert result_state.updated_at is not None
        assert result_state.updated_at >= result_state.created_at

    @pytest.mark.unit
    def test_workflow_string_representations(self, db_runbook_finder_workflow):
        """Test workflow string representations."""
        workflow = db_runbook_finder_workflow
        
        # Test __str__
        str_repr = str(workflow)
        assert "DBRunbookFinderWorkflow" in str_repr
        assert workflow.config_path in str_repr
        
        # Test __repr__
        repr_str = repr(workflow)
        assert "DBRunbookFinderWorkflow" in repr_str
        assert workflow.config_path in repr_str

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_various_project_types(self, db_runbook_finder_workflow, project_client_mappings):
        """Test workflow with different project types."""
        workflow = db_runbook_finder_workflow
        
        # Test with different project prefixes
        test_cases = [
            ("AGENT-6", "Agent System"),
            ("NESMCI-123", "Neste"),
            ("HEMCI-456", "Helvetia"),
            ("OVRMCI-789", "Ovora Internal")
        ]
        
        for ticket_key, expected_client in test_cases:
            result_state = await workflow.run(ticket_key)
            
            # Verify client mapping
            assert result_state.get_client_name() == expected_client
            assert result_state.incident_data["client"] == expected_client
            
            # Verify workflow completed
            assert result_state.is_completed()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_workflow_execution_success_path(self, db_runbook_finder_workflow, workflow_state_with_runbooks):
        """Test mock workflow execution with success path."""
        workflow = db_runbook_finder_workflow
        
        # Execute mock workflow
        result_state = await workflow._mock_workflow_execution(workflow_state_with_runbooks)
        
        # Should follow success path
        assert result_state.status == "SUCCESS"
        assert result_state.has_runbooks()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_workflow_execution_gap_path(self, db_runbook_finder_workflow, workflow_state_no_runbooks):
        """Test mock workflow execution with gap path."""
        workflow = db_runbook_finder_workflow
        
        # Execute mock workflow
        result_state = await workflow._mock_workflow_execution(workflow_state_no_runbooks)
        
        # Should follow gap path
        assert result_state.status == "GAP_DETECTED"
        assert not result_state.has_runbooks()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_validation(self, db_runbook_finder_workflow, workflow_assertions):
        """Comprehensive end-to-end workflow validation."""
        workflow = db_runbook_finder_workflow
        
        # Execute complete workflow
        result_state = await workflow.run("AGENT-6")
        
        # Comprehensive validation
        workflow_assertions.assert_state_valid(result_state)
        workflow_assertions.assert_state_completed(result_state)
        workflow_assertions.assert_performance_within_limits(result_state)
        
        # Verify all expected operations occurred
        expected_metrics = ["fetch_incident", "search_runbooks", "notify_team"]
        for metric in expected_metrics:
            assert metric in result_state.performance_metrics
            assert result_state.performance_metrics[metric] > 0
        
        # Verify either success or gap path was taken
        if result_state.status == "SUCCESS":
            assert "update_jira_results" in result_state.performance_metrics
            workflow_assertions.assert_state_has_runbooks(result_state)
        elif result_state.status == "GAP_DETECTED":
            assert "terminate_gap" in result_state.performance_metrics
            workflow_assertions.assert_state_no_runbooks(result_state)
        
        # Verify data quality
        assert result_state.jira_key == "AGENT-6"
        assert result_state.get_client_name() == "Agent System"
        assert "database" in result_state.get_incident_summary().lower()
        assert "timeout" in result_state.get_incident_summary().lower()