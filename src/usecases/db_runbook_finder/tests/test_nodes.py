"""
Unit tests for DB Runbook Finder workflow nodes.

This module contains comprehensive tests for all individual workflow nodes,
testing both success and error scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ..state import WorkflowState
from ..nodes import DBRunbookFinderNodes


class TestDBRunbookFinderNodes:
    """Test suite for DB Runbook Finder workflow nodes."""

    @pytest.mark.unit
    def test_project_to_client_mapping(self, db_runbook_finder_nodes):
        """Test project key to client name mapping."""
        nodes = db_runbook_finder_nodes
        
        # Test known mappings
        assert nodes.PROJECT_TO_CLIENT_MAP["AGENT"] == "Agent System"
        assert nodes.PROJECT_TO_CLIENT_MAP["NESMCI"] == "Neste"
        assert nodes.PROJECT_TO_CLIENT_MAP["HEMCI"] == "Helvetia"
        assert nodes.PROJECT_TO_CLIENT_MAP["OVRMCI"] == "Ovora Internal"
        
        # Test mapping contains AGENT-6 project
        assert "AGENT" in nodes.PROJECT_TO_CLIENT_MAP

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_incident_node_success(self, db_runbook_finder_nodes, sample_workflow_state):
        """Test successful incident fetching."""
        nodes = db_runbook_finder_nodes
        
        # Execute node
        result_state = await nodes.fetch_incident_node(sample_workflow_state)
        
        # Verify state updates
        assert result_state.incident_data is not None
        assert result_state.incident_data["summary"] != ""
        assert result_state.incident_data["client"] == "Agent System"
        assert result_state.incident_data["project_key"] == "AGENT"
        assert "fetch_incident" in result_state.performance_metrics
        assert not result_state.is_error_state()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_incident_node_unknown_project(self, db_runbook_finder_nodes):
        """Test incident fetching with unknown project key."""
        nodes = db_runbook_finder_nodes
        state = WorkflowState(jira_key="UNKNOWN-123")
        
        # Execute node
        result_state = await nodes.fetch_incident_node(state)
        
        # Verify unknown client mapping
        assert result_state.incident_data["client"] == "Unknown"
        assert result_state.incident_data["project_key"] == "UNKNOWN"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_runbooks_node_success(self, db_runbook_finder_nodes, populated_workflow_state):
        """Test successful runbook search."""
        nodes = db_runbook_finder_nodes
        
        # Execute node
        result_state = await nodes.search_runbooks_node(populated_workflow_state)
        
        # Verify runbook results
        assert result_state.runbooks is not None
        assert len(result_state.runbooks) > 0
        assert "search_runbooks" in result_state.performance_metrics
        assert not result_state.is_error_state()
        
        # Verify search results structure
        for runbook in result_state.runbooks:
            assert "title" in runbook
            assert "url" in runbook
            assert "space_key" in runbook
            assert "relevance_score" in runbook

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_runbooks_node_empty_query(self, db_runbook_finder_nodes, sample_workflow_state):
        """Test runbook search with empty query."""
        nodes = db_runbook_finder_nodes
        
        # Set empty incident data
        sample_workflow_state.incident_data = {"summary": "", "description": ""}
        
        # Execute node
        result_state = await nodes.search_runbooks_node(sample_workflow_state)
        
        # Verify empty results
        assert result_state.runbooks == []
        assert not result_state.is_error_state()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_runbooks_node_gap_scenario(self, db_runbook_finder_nodes):
        """Test runbook search that returns no results (gap scenario)."""
        nodes = db_runbook_finder_nodes
        state = WorkflowState(jira_key="TEST-999")
        state.incident_data = {
            "summary": "Unknown issue type",
            "description": "This is a completely novel issue"
        }
        
        # Execute node
        result_state = await nodes.search_runbooks_node(state)
        
        # Should return empty results but not error
        assert result_state.runbooks == []
        assert not result_state.is_error_state()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_jira_with_results_node_success(self, db_runbook_finder_nodes, workflow_state_with_runbooks):
        """Test successful Jira update with runbook results."""
        nodes = db_runbook_finder_nodes
        
        # Execute node
        result_state = await nodes.update_jira_with_results_node(workflow_state_with_runbooks)
        
        # Verify success status
        assert result_state.status == "SUCCESS"
        assert "update_jira_results" in result_state.performance_metrics
        assert not result_state.is_error_state()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_terminate_with_gap_error_node_success(self, db_runbook_finder_nodes, workflow_state_no_runbooks):
        """Test successful gap handling."""
        nodes = db_runbook_finder_nodes
        
        # Execute node
        result_state = await nodes.terminate_with_gap_error_node(workflow_state_no_runbooks)
        
        # Verify gap status
        assert result_state.status == "GAP_DETECTED"
        assert "terminate_gap" in result_state.performance_metrics
        assert not result_state.is_error_state()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_notify_team_node_success_scenario(self, db_runbook_finder_nodes, workflow_state_with_runbooks):
        """Test team notification for success scenario."""
        nodes = db_runbook_finder_nodes
        
        # Set success status
        workflow_state_with_runbooks.update_status("SUCCESS")
        
        # Execute node
        result_state = await nodes.notify_team_node(workflow_state_with_runbooks)
        
        # Verify notification was processed
        assert "notify_team" in result_state.performance_metrics
        assert result_state.status == "SUCCESS"  # Status should remain unchanged

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_notify_team_node_gap_scenario(self, db_runbook_finder_nodes, workflow_state_no_runbooks):
        """Test team notification for gap scenario."""
        nodes = db_runbook_finder_nodes
        
        # Set gap status
        workflow_state_no_runbooks.update_status("GAP_DETECTED")
        
        # Execute node
        result_state = await nodes.notify_team_node(workflow_state_no_runbooks)
        
        # Verify notification was processed
        assert "notify_team" in result_state.performance_metrics
        assert result_state.status == "GAP_DETECTED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_notify_team_node_error_scenario(self, db_runbook_finder_nodes, sample_workflow_state):
        """Test team notification for error scenario."""
        nodes = db_runbook_finder_nodes
        
        # Set error status
        sample_workflow_state.update_status("ERROR", "Test error message")
        
        # Execute node
        result_state = await nodes.notify_team_node(sample_workflow_state)
        
        # Verify notification was processed
        assert "notify_team" in result_state.performance_metrics
        assert result_state.status == "ERROR"

    @pytest.mark.unit
    def test_mock_jira_response_agent_6(self, db_runbook_finder_nodes):
        """Test mock Jira response for AGENT-6."""
        nodes = db_runbook_finder_nodes
        
        response = nodes._get_mock_jira_response("AGENT-6")
        
        # Verify structure
        assert "fields" in response
        fields = response["fields"]
        assert "summary" in fields
        assert "description" in fields
        assert fields["project"]["key"] == "AGENT"
        assert "database" in fields["summary"].lower()
        assert "timeout" in fields["summary"].lower()

    @pytest.mark.unit
    def test_mock_jira_response_unknown_ticket(self, db_runbook_finder_nodes):
        """Test mock Jira response for unknown ticket."""
        nodes = db_runbook_finder_nodes
        
        response = nodes._get_mock_jira_response("UNKNOWN-999")
        
        # Verify fallback response
        assert "fields" in response
        fields = response["fields"]
        assert "Mock incident" in fields["summary"]
        assert fields["project"]["key"] == "UNKNOWN"

    @pytest.mark.unit
    def test_mock_confluence_response_database_query(self, db_runbook_finder_nodes):
        """Test mock Confluence response for database-related query."""
        nodes = db_runbook_finder_nodes
        
        response = nodes._get_mock_confluence_response("database timeout issue", "AGENT-6")
        
        # Verify database-related results
        assert "results" in response
        results = response["results"]
        assert len(results) > 0
        
        # Check for database-related content
        titles = [r["title"] for r in results]
        assert any("Database" in title for title in titles)
        assert any("Connection" in title for title in titles)

    @pytest.mark.unit
    def test_mock_confluence_response_empty_results(self, db_runbook_finder_nodes):
        """Test mock Confluence response that returns no results."""
        nodes = db_runbook_finder_nodes
        
        response = nodes._get_mock_confluence_response("completely unknown issue", "TEST-999")
        
        # Verify empty results (gap scenario)
        assert "results" in response
        assert response["results"] == []

    @pytest.mark.unit
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_node_performance_within_limits(self, db_runbook_finder_nodes, populated_workflow_state, workflow_assertions):
        """Test that individual nodes complete within performance limits."""
        nodes = db_runbook_finder_nodes
        
        # Test each node individually
        start_time = datetime.utcnow()
        
        # Fetch incident
        state = await nodes.fetch_incident_node(populated_workflow_state)
        assert state.performance_metrics["fetch_incident"] < 5.0  # Should be very fast for mock
        
        # Search runbooks
        state = await nodes.search_runbooks_node(state)
        assert state.performance_metrics["search_runbooks"] < 5.0
        
        # Update Jira (success path)
        if state.has_runbooks():
            state = await nodes.update_jira_with_results_node(state)
            assert state.performance_metrics["update_jira_results"] < 5.0
        
        # Notify team
        state = await nodes.notify_team_node(state)
        assert state.performance_metrics["notify_team"] < 5.0
        
        # Check total performance
        workflow_assertions.assert_performance_within_limits(state, max_duration=10.0)

    @pytest.mark.unit
    @pytest.mark.error_handling
    @pytest.mark.asyncio
    async def test_node_error_handling(self, db_runbook_finder_nodes, sample_workflow_state):
        """Test error handling in nodes."""
        nodes = db_runbook_finder_nodes
        
        # Test with invalid state
        invalid_state = WorkflowState(jira_key="")
        
        # Should handle gracefully
        try:
            await nodes.fetch_incident_node(invalid_state)
        except ValueError:
            # Expected for empty jira_key
            pass

    @pytest.mark.unit
    def test_node_initialization(self):
        """Test proper node initialization."""
        nodes = DBRunbookFinderNodes()
        
        # Verify initialization
        assert nodes.PROJECT_TO_CLIENT_MAP is not None
        assert len(nodes.PROJECT_TO_CLIENT_MAP) > 0
        assert hasattr(nodes, 'logger')
        assert hasattr(nodes, 'config')

    @pytest.mark.unit
    def test_project_client_mapping_completeness(self, db_runbook_finder_nodes, project_client_mappings):
        """Test that all expected project mappings are present."""
        nodes = db_runbook_finder_nodes
        
        # Verify key mappings are present
        expected_projects = ["AGENT", "NESMCI", "HEMCI", "OVRMCI", "OVR"]
        for project in expected_projects:
            assert project in nodes.PROJECT_TO_CLIENT_MAP
            assert nodes.PROJECT_TO_CLIENT_MAP[project] != ""
            assert nodes.PROJECT_TO_CLIENT_MAP[project] != "Unknown"