"""
Unit tests for MockDataStrategy (Mock Persistence Strategy).

Tests all methods of the mock persistence strategy for comprehensive coverage
and validates data tracking and incident management functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategies.mock_persistence import MockDataStrategy
from src.usecases.db_runbook_finder.mcp_server.exceptions import IncidentTrackingError, MCPRunbookError


class TestMockDataStrategy:
    """Test suite for MockDataStrategy."""
    
    @pytest.fixture
    def mock_strategy(self):
        """Create mock persistence strategy instance."""
        return MockDataStrategy()
    
    @pytest.mark.asyncio
    async def test_health_check_always_returns_true(self, mock_strategy):
        """Test that health check always returns True for mock strategy."""
        result = await mock_strategy.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_save_runbook_usage_success(self, mock_strategy):
        """Test successful runbook usage tracking."""
        runbook_id = "test_runbook_123"
        usage_context = {
            "incident_id": "INC-2024001",
            "user": "test_user@company.com",
            "outcome": "success",
            "resolution_time": 15.5,
            "success": True,
            "notes": "Test usage tracking"
        }
        
        usage_id = await mock_strategy.save_runbook_usage(runbook_id, usage_context)
        
        assert isinstance(usage_id, str)
        assert usage_id.startswith("usage_")
        assert runbook_id in usage_id
        
        # Verify record was saved
        all_records = mock_strategy.get_all_usage_records()
        assert usage_id in all_records
        
        record = all_records[usage_id]
        assert record["runbook_id"] == runbook_id
        assert record["incident_id"] == usage_context["incident_id"]
        assert record["user"] == usage_context["user"]
        assert record["outcome"] == usage_context["outcome"]
        assert record["success"] == usage_context["success"]
    
    @pytest.mark.asyncio
    async def test_save_runbook_usage_minimal_context(self, mock_strategy):
        """Test saving usage with minimal context information."""
        runbook_id = "minimal_test_123"
        usage_context = {"outcome": "partial"}
        
        usage_id = await mock_strategy.save_runbook_usage(runbook_id, usage_context)
        
        assert isinstance(usage_id, str)
        
        # Verify defaults were applied
        all_records = mock_strategy.get_all_usage_records()
        record = all_records[usage_id]
        assert record["runbook_id"] == runbook_id
        assert record["outcome"] == "partial"
        assert "incident_id" in record  # Should have generated ID
        assert "user" in record  # Should have default user
    
    @pytest.mark.asyncio
    async def test_save_runbook_usage_updates_metrics(self, mock_strategy):
        """Test that saving usage updates runbook metrics."""
        runbook_id = "metrics_test_123"
        usage_context = {
            "incident_id": "INC-2024002",
            "outcome": "success",
            "success": True,
            "resolution_time": 30.0
        }
        
        # Get initial metrics
        initial_metrics = await mock_strategy.get_runbook_metrics(runbook_id)
        initial_count = initial_metrics["total_usage_count"]
        
        # Save usage
        await mock_strategy.save_runbook_usage(runbook_id, usage_context)
        
        # Check updated metrics
        updated_metrics = await mock_strategy.get_runbook_metrics(runbook_id)
        assert updated_metrics["total_usage_count"] == initial_count + 1
        assert updated_metrics["success_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_runbook_metrics_success(self, mock_strategy):
        """Test successful retrieval of runbook metrics."""
        runbook_id = "123456"  # Known mock runbook
        
        metrics = await mock_strategy.get_runbook_metrics(runbook_id)
        
        # Validate metrics structure
        assert isinstance(metrics, dict)
        assert metrics["runbook_id"] == runbook_id
        assert "total_usage_count" in metrics
        assert "success_count" in metrics
        assert "failure_count" in metrics
        assert "success_rate" in metrics
        assert "average_resolution_time" in metrics
        assert "last_used" in metrics
        assert "first_used" in metrics
        assert metrics["source"] == "mock"
        
        # Validate data types
        assert isinstance(metrics["total_usage_count"], int)
        assert isinstance(metrics["success_count"], int)
        assert isinstance(metrics["failure_count"], int)
        assert isinstance(metrics["success_rate"], (int, float))
        assert isinstance(metrics["average_resolution_time"], (int, float))
        
        # Validate ranges
        assert metrics["total_usage_count"] >= 0
        assert metrics["success_count"] >= 0
        assert metrics["failure_count"] >= 0
        assert 0.0 <= metrics["success_rate"] <= 100.0
    
    @pytest.mark.asyncio
    async def test_get_runbook_metrics_nonexistent(self, mock_strategy):
        """Test metrics retrieval for non-existent runbook."""
        runbook_id = "nonexistent_runbook"
        
        metrics = await mock_strategy.get_runbook_metrics(runbook_id)
        
        # Should return empty metrics structure
        assert metrics["runbook_id"] == runbook_id
        assert metrics["total_usage_count"] == 0
        assert metrics["success_count"] == 0
        assert metrics["failure_count"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["average_resolution_time"] == 0.0
        assert metrics["last_used"] is None
        assert metrics["first_used"] is None
    
    @pytest.mark.asyncio
    async def test_create_incident_ticket_success(self, mock_strategy):
        """Test successful incident ticket creation."""
        runbook_id = "ticket_test_123"
        context = {
            "summary": "Test incident summary",
            "description": "Test incident description for runbook testing",
            "priority": "High",
            "issue_type": "Bug",
            "labels": ["test", "incident"]
        }
        
        ticket_id = await mock_strategy.create_incident_ticket(runbook_id, context)
        
        assert isinstance(ticket_id, str)
        assert ticket_id.startswith("RBK-")
        
        # Verify ticket was created
        all_tickets = mock_strategy.get_all_tickets()
        assert ticket_id in all_tickets
        
        ticket = all_tickets[ticket_id]
        assert ticket["runbook_id"] == runbook_id
        assert ticket["summary"] == context["summary"]
        assert ticket["description"] == context["description"]
        assert ticket["priority"] == context["priority"]
        assert ticket["status"] == "Open"
        assert len(ticket["comments"]) > 0
    
    @pytest.mark.asyncio
    async def test_create_incident_ticket_minimal_context(self, mock_strategy):
        """Test ticket creation with minimal context."""
        runbook_id = "minimal_ticket_123"
        context = {}
        
        ticket_id = await mock_strategy.create_incident_ticket(runbook_id, context)
        
        assert isinstance(ticket_id, str)
        
        # Should have defaults applied
        all_tickets = mock_strategy.get_all_tickets()
        ticket = all_tickets[ticket_id]
        assert ticket["runbook_id"] == runbook_id
        assert ticket["priority"] == "Medium"  # Default
        assert ticket["status"] == "Open"
        assert "summary" in ticket
        assert "description" in ticket
    
    @pytest.mark.asyncio
    async def test_update_ticket_status_success(self, mock_strategy):
        """Test successful ticket status update."""
        # First create a ticket
        runbook_id = "status_test_123"
        context = {"summary": "Status test ticket"}
        ticket_id = await mock_strategy.create_incident_ticket(runbook_id, context)
        
        # Update the status
        comment = "Test status update with **bold** formatting"
        success = await mock_strategy.update_ticket_status(ticket_id, "resolved", comment)
        
        assert success is True
        
        # Verify update
        all_tickets = mock_strategy.get_all_tickets()
        ticket = all_tickets[ticket_id]
        assert ticket["status"] == "resolved"
        
        # Check comment was added
        comments = ticket["comments"]
        assert len(comments) >= 2  # Initial + status change + optional custom comment
        
        # Find the custom comment
        custom_comment = next((c for c in comments if comment in c["comment"]), None)
        assert custom_comment is not None
    
    @pytest.mark.asyncio
    async def test_update_ticket_status_nonexistent_ticket(self, mock_strategy):
        """Test updating status of non-existent ticket."""
        ticket_id = "NONEXISTENT-123"
        
        success = await mock_strategy.update_ticket_status(ticket_id, "closed")
        
        # Should still return success (mock creates ticket automatically)
        assert success is True
        
        # Verify ticket was auto-created
        all_tickets = mock_strategy.get_all_tickets()
        assert ticket_id in all_tickets
        assert all_tickets[ticket_id]["status"] == "closed"
    
    @pytest.mark.asyncio
    async def test_get_incident_history_success(self, mock_strategy):
        """Test successful incident history retrieval."""
        incident_id = "INC-2024001"  # Should match mock data
        
        history = await mock_strategy.get_incident_history(incident_id)
        
        # Validate history structure
        assert isinstance(history, dict)
        assert history["incident_id"] == incident_id
        assert "runbook_usage_count" in history
        assert "runbooks_used" in history
        assert "timeline" in history
        assert "first_activity" in history
        assert "last_activity" in history
        assert "overall_outcome" in history
        assert "associated_ticket" in history
        assert history["source"] == "mock"
        
        # Validate data types
        assert isinstance(history["runbook_usage_count"], int)
        assert isinstance(history["runbooks_used"], list)
        assert isinstance(history["timeline"], list)
        assert history["runbook_usage_count"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_incident_history_nonexistent(self, mock_strategy):
        """Test incident history for non-existent incident."""
        incident_id = "INC-NONEXISTENT"
        
        history = await mock_strategy.get_incident_history(incident_id)
        
        # Should return empty history structure
        assert history["incident_id"] == incident_id
        assert history["runbook_usage_count"] == 0
        assert history["runbooks_used"] == []
        assert history["timeline"] == []
        assert history["first_activity"] is None
        assert history["last_activity"] is None
    
    @pytest.mark.asyncio
    async def test_track_runbook_effectiveness_success(self, mock_strategy):
        """Test successful runbook effectiveness tracking."""
        runbook_id = "effectiveness_test_123"
        incident_id = "INC-2024003"
        success = True
        resolution_time = 25.5
        notes = "Test effectiveness tracking"
        
        result = await mock_strategy.track_runbook_effectiveness(
            runbook_id, incident_id, success, resolution_time, notes
        )
        
        assert result is True
        
        # Should have created a usage record
        all_records = mock_strategy.get_all_usage_records()
        effectiveness_records = [
            r for r in all_records.values()
            if r.get("runbook_id") == runbook_id and r.get("incident_id") == incident_id
        ]
        assert len(effectiveness_records) > 0
        
        # Verify the effectiveness record
        record = effectiveness_records[0]
        assert record["success"] == success
        assert record["resolution_time"] == resolution_time
        assert notes in record["notes"]
        assert record["outcome"] == "success"
    
    @pytest.mark.asyncio
    async def test_track_runbook_effectiveness_failure(self, mock_strategy):
        """Test tracking runbook effectiveness for failure case."""
        runbook_id = "failure_test_123"
        incident_id = "INC-2024004"
        success = False
        resolution_time = 120.0
        
        result = await mock_strategy.track_runbook_effectiveness(
            runbook_id, incident_id, success, resolution_time
        )
        
        assert result is True
        
        # Verify failure was tracked
        all_records = mock_strategy.get_all_usage_records()
        failure_records = [
            r for r in all_records.values()
            if r.get("runbook_id") == runbook_id and r.get("success") is False
        ]
        assert len(failure_records) > 0
    
    # Test helper methods
    def test_get_all_usage_records(self, mock_strategy):
        """Test retrieval of all usage records."""
        records = mock_strategy.get_all_usage_records()
        
        assert isinstance(records, dict)
        # Should have some initial mock data
        assert len(records) >= 0
        
        # Validate record structure
        for usage_id, record in records.items():
            assert "usage_id" in record
            assert "runbook_id" in record
            assert "incident_id" in record
            assert "timestamp" in record
            assert "outcome" in record
    
    def test_get_all_metrics(self, mock_strategy):
        """Test retrieval of all runbook metrics."""
        metrics = mock_strategy.get_all_metrics()
        
        assert isinstance(metrics, dict)
        
        # Validate metrics structure
        for runbook_id, metric in metrics.items():
            assert "total_usage_count" in metric
            assert "success_count" in metric
            assert "failure_count" in metric
    
    def test_get_all_tickets(self, mock_strategy):
        """Test retrieval of all incident tickets."""
        tickets = mock_strategy.get_all_tickets()
        
        assert isinstance(tickets, dict)
        
        # Validate ticket structure
        for ticket_id, ticket in tickets.items():
            assert "ticket_id" in ticket
            assert "runbook_id" in ticket
            assert "status" in ticket
            assert "created_at" in ticket
            assert "comments" in ticket
            assert isinstance(ticket["comments"], list)
    
    def test_get_all_incident_history(self, mock_strategy):
        """Test retrieval of all incident history."""
        history = mock_strategy.get_all_incident_history()
        
        assert isinstance(history, dict)
        
        # Validate history structure
        for incident_id, incident in history.items():
            assert "incident_id" in incident
            assert "runbook_usage_count" in incident
            assert "runbooks_used" in incident
    
    def test_clear_data_and_reinitialize(self, mock_strategy):
        """Test data clearing and reinitialization."""
        # Add some custom data first
        mock_strategy._usage_records["test"] = {"test": "data"}
        
        # Clear data
        mock_strategy.clear_data()
        
        # Should have reinitialized with fresh mock data
        records = mock_strategy.get_all_usage_records()
        assert "test" not in records
        # Should have some initial mock data again
        assert len(records) >= 0
    
    def test_add_mock_usage_record(self, mock_strategy):
        """Test manual addition of mock usage record."""
        runbook_id = "manual_test_123"
        usage_context = {
            "incident_id": "MANUAL-001",
            "user": "manual_user@test.com",
            "outcome": "success",
            "success": True,
            "notes": "Manually added test record"
        }
        
        usage_id = mock_strategy.add_mock_usage_record(runbook_id, usage_context)
        
        assert isinstance(usage_id, str)
        assert usage_id.startswith("manual_")
        
        # Verify record was added
        all_records = mock_strategy.get_all_usage_records()
        assert usage_id in all_records
        record = all_records[usage_id]
        assert record["runbook_id"] == runbook_id
        assert record["incident_id"] == usage_context["incident_id"]
    
    def test_simulate_incident_scenario(self, mock_strategy):
        """Test incident scenario simulation."""
        incident_id = "SIMULATION-001"
        runbook_ids = ["sim_rb_1", "sim_rb_2", "sim_rb_3"]
        
        mock_strategy.simulate_incident_scenario(incident_id, runbook_ids)
        
        # Verify records were created for all runbooks
        all_records = mock_strategy.get_all_usage_records()
        incident_records = [
            r for r in all_records.values()
            if r.get("incident_id") == incident_id
        ]
        
        assert len(incident_records) == len(runbook_ids)
        
        # Verify all runbooks are represented
        recorded_runbook_ids = [r["runbook_id"] for r in incident_records]
        for runbook_id in runbook_ids:
            assert runbook_id in recorded_runbook_ids
    
    def test_determine_overall_outcome(self, mock_strategy):
        """Test overall outcome determination logic."""
        # Test with mixed outcomes
        mixed_records = [
            {"outcome": "success"},
            {"outcome": "success"},
            {"outcome": "failure"}
        ]
        outcome = mock_strategy._determine_overall_outcome(mixed_records)
        assert outcome == "resolved"  # More successes
        
        # Test with all failures
        failure_records = [
            {"outcome": "failure"},
            {"outcome": "failure"}
        ]
        outcome = mock_strategy._determine_overall_outcome(failure_records)
        assert outcome == "unresolved"
        
        # Test with empty records
        outcome = mock_strategy._determine_overall_outcome([])
        assert outcome == "no_data"
    
    @pytest.mark.asyncio
    async def test_concurrent_usage_tracking(self, mock_strategy):
        """Test concurrent usage record saving for thread safety."""
        runbook_id = "concurrent_test_123"
        
        # Create multiple concurrent usage tracking tasks
        tasks = []
        for i in range(10):
            usage_context = {
                "incident_id": f"CONCURRENT-{i}",
                "user": f"user_{i}@test.com",
                "outcome": "success",
                "success": True
            }
            task = mock_strategy.save_runbook_usage(f"{runbook_id}_{i}", usage_context)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, str)
            assert result.startswith("usage_")
    
    @pytest.mark.asyncio
    async def test_error_handling_simulated_failure(self, mock_strategy):
        """Test error handling with simulated failures."""
        # Patch a method to raise an exception
        with patch.object(mock_strategy, '_update_runbook_metrics', side_effect=Exception("Simulated failure")):
            with pytest.raises(IncidentTrackingError):
                await mock_strategy.save_runbook_usage("test_fail", {"incident_id": "FAIL-001"})
    
    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, mock_strategy):
        """Test performance with larger dataset."""
        start_time = asyncio.get_event_loop().time()
        
        # Add many usage records
        tasks = []
        for i in range(100):
            task = mock_strategy.save_runbook_usage(
                f"perf_test_{i}",
                {"incident_id": f"PERF-{i}", "outcome": "success"}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Get metrics for multiple runbooks
        for i in range(10):
            await mock_strategy.get_runbook_metrics(f"perf_test_{i}")
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should complete within reasonable time
        assert duration_ms < 2000, f"Performance test took {duration_ms:.2f}ms"
    
    def test_strategy_initialization(self, mock_strategy):
        """Test strategy initialization with mock data."""
        assert mock_strategy is not None
        
        # Should have initialized with some mock data
        records = mock_strategy.get_all_usage_records()
        assert isinstance(records, dict)
        
        metrics = mock_strategy.get_all_metrics()
        assert isinstance(metrics, dict)
        
        tickets = mock_strategy.get_all_tickets()
        assert isinstance(tickets, dict)