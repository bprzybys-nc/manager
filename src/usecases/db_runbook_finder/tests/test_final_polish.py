"""
Tests for DB Runbook Finder final polish improvements.

This module tests the three main polish improvements:
1. Slack API compliance with text argument
2. Relevance scoring enhancements 
3. Metrics formatting standardization
"""

import pytest
from unittest.mock import patch, MagicMock
from src.usecases.db_runbook_finder.nodes import DBRunbookFinderNodes
from src.usecases.db_runbook_finder.state import WorkflowState, MetricsFormatter


class TestSlackAPICompliance:
    """Test Slack API accessibility compliance."""
    
    @pytest.fixture
    def nodes(self):
        """Create DBRunbookFinderNodes instance for testing."""
        return DBRunbookFinderNodes(use_real_tools=False)
    
    @pytest.fixture
    def success_state(self):
        """Create a successful workflow state for testing."""
        state = WorkflowState(jira_key="TEST-1")
        state.status = "SUCCESS"
        state.incident_data = {
            "summary": "Database connection timeout",
            "client": "Test Client"
        }
        state.runbooks = [
            {"title": "Test Runbook", "relevance_score": 0.85}
        ]
        return state
    
    def test_accessible_summary_creation(self, nodes):
        """Test plain text summary creation for different statuses."""
        test_cases = [
            ("SUCCESS", "Runbook Recommendations Found"),
            ("GAP_DETECTED", "Runbook Gap Detected"),
            ("ERROR", "Workflow Error")
        ]
        
        for status, expected_text in test_cases:
            state = WorkflowState(jira_key="TEST-1")
            state.status = status
            state.runbooks = [{"title": "Test"}] if status == "SUCCESS" else []
            
            summary = nodes._create_accessible_summary(state)
            
            assert expected_text in summary
            assert "TEST-1" in summary
            assert len(summary) < 200  # Reasonable length for notifications

    def test_accessible_summary_with_runbook_count(self, nodes):
        """Test that SUCCESS summary includes runbook count."""
        state = WorkflowState(jira_key="TEST-123")
        state.status = "SUCCESS"
        state.runbooks = [
            {"title": "Runbook 1"},
            {"title": "Runbook 2"},
            {"title": "Runbook 3"}
        ]
        
        summary = nodes._create_accessible_summary(state)
        
        assert "Runbook Recommendations Found" in summary
        assert "TEST-123" in summary
        assert "3 recommendations found" in summary

    def test_accessible_summary_gap_scenario(self, nodes):
        """Test GAP_DETECTED summary format."""
        state = WorkflowState(jira_key="GAP-456")
        state.status = "GAP_DETECTED"
        state.runbooks = []
        
        summary = nodes._create_accessible_summary(state)
        
        assert "Runbook Gap Detected" in summary
        assert "GAP-456" in summary
        assert "manual intervention required" in summary

    def test_accessible_summary_error_scenario(self, nodes):
        """Test ERROR summary format."""
        state = WorkflowState(jira_key="ERR-789")
        state.status = "ERROR"
        state.error_message = "Test error occurred"
        
        summary = nodes._create_accessible_summary(state)
        
        assert "Workflow Error" in summary
        assert "ERR-789" in summary
        assert "check logs" in summary


class TestRelevanceScoring:
    """Test relevance scoring enhancements."""
    
    def test_keyword_boosting_enhancement(self):
        """Test domain-specific keyword boosting."""
        # Import the vector store class to test enhancement
        from src.tools.confluence.app.vector_store import VectorStore
        
        # Create a mock vector store instance
        vector_store = VectorStore(collection_name='test-collection')
        
        query = "database connection timeout"
        content = "database connection timeout troubleshooting guide"
        base_score = 0.60
        
        # Test enhancement calculation
        enhanced_score = vector_store._enhance_relevance_score(query, content, base_score)
        
        # Should boost score due to keyword matches
        assert enhanced_score > base_score
        assert enhanced_score <= 1.0  # Should not exceed 1.0
        
        # Calculate expected boost
        db_keywords = [
            "database", "connection", "timeout", "performance", "backup", "recovery",
            "sql", "query", "index", "table", "schema", "migration", "replication",
            "monitoring", "troubleshooting", "optimization", "tuning", "memory",
            "disk", "storage", "maintenance", "patch", "upgrade", "configuration"
        ]
        matching_keywords = sum(1 for kw in db_keywords 
                               if kw in query.lower() and kw in content.lower())
        expected_boost = min(matching_keywords * 0.05, 0.20)
        expected_score = min(base_score + expected_boost, 1.0)
        
        assert enhanced_score == expected_score

    def test_keyword_boosting_no_matches(self):
        """Test enhancement with no keyword matches."""
        from src.tools.confluence.app.vector_store import VectorStore
        
        vector_store = VectorStore(collection_name='test-collection')
        
        query = "general application issue"
        content = "generic troubleshooting steps"
        base_score = 0.50
        
        enhanced_score = vector_store._enhance_relevance_score(query, content, base_score)
        
        # Should return base score when no keywords match
        assert enhanced_score == base_score

    def test_keyword_boosting_max_limit(self):
        """Test that keyword boosting respects maximum limit."""
        from src.tools.confluence.app.vector_store import VectorStore
        
        vector_store = VectorStore(collection_name='test-collection')
        
        # Query and content with many database keywords
        query = "database connection timeout performance backup recovery sql query index"
        content = "database connection timeout performance backup recovery sql query index troubleshooting"
        base_score = 0.60
        
        enhanced_score = vector_store._enhance_relevance_score(query, content, base_score)
        
        # Should not exceed base_score + 0.20 (20% max boost)
        assert enhanced_score <= base_score + 0.20
        assert enhanced_score <= 1.0

    def test_keyword_boosting_boundary_case(self):
        """Test enhancement when base score is already high."""
        from src.tools.confluence.app.vector_store import VectorStore
        
        vector_store = VectorStore(collection_name='test-collection')
        
        query = "database connection troubleshooting"
        content = "database connection troubleshooting guide"
        base_score = 0.95  # Already high score
        
        enhanced_score = vector_store._enhance_relevance_score(query, content, base_score)
        
        # Should cap at 1.0 even with boosting
        assert enhanced_score == 1.0


class TestMetricsFormatting:
    """Test metrics formatting standardization."""
    
    def test_duration_formatting(self):
        """Test duration formatting with appropriate units."""
        test_cases = [
            (0.001, "1ms"),      # Sub-second as milliseconds
            (0.085, "85ms"),     # Sub-second as milliseconds
            (1.234, "1.23s"),    # Seconds with 2 decimal places
            (65.789, "65.79s")   # Larger durations in seconds
        ]
        
        for duration, expected in test_cases:
            result = MetricsFormatter.format_duration(duration)
            assert result == expected

    def test_percentage_formatting(self):
        """Test percentage formatting with 1 decimal precision."""
        test_cases = [
            (0.892, "89.2%"),
            (0.50, "50.0%"),
            (0.995, "99.5%"),
            (0.0, "0.0%"),
            (1.0, "100.0%")
        ]
        
        for score, expected in test_cases:
            result = MetricsFormatter.format_percentage(score)
            assert result == expected

    def test_metric_formatting(self):
        """Test generic metric formatting with units."""
        test_cases = [
            (1.23456, "MB", "1.23MB"),
            (999.999, "KB", "1000.00KB"),
            (0.1, "GB", "0.10GB")
        ]
        
        for value, unit, expected in test_cases:
            result = MetricsFormatter.format_metric(value, unit)
            assert result == expected

    def test_workflow_state_formatted_metrics(self):
        """Test WorkflowState returns consistently formatted metrics."""
        state = WorkflowState(jira_key="TEST-1")
        
        # Add some performance metrics
        state.add_performance_metric("fetch_incident", 1.5)
        state.add_performance_metric("search_runbooks", 2.1)
        state.add_performance_metric("update_jira", 0.5)
        
        formatted_duration = state.get_formatted_duration()
        metrics_summary = state.get_metrics_summary()
        
        # Total should be 4.1 seconds
        assert formatted_duration == "4.10s"
        assert "total_duration" in metrics_summary
        assert metrics_summary["total_duration"] == "4.10s"
        assert "s" in formatted_duration  # Has units

    def test_workflow_state_sub_second_formatting(self):
        """Test formatting when total duration is sub-second."""
        state = WorkflowState(jira_key="TEST-1")
        
        # Add metrics totaling less than 1 second
        state.add_performance_metric("quick_operation", 0.250)
        state.add_performance_metric("another_quick_op", 0.350)
        
        formatted_duration = state.get_formatted_duration()
        
        # Total is 0.6s, should be formatted as "600ms"
        assert formatted_duration == "600ms"

    def test_metrics_summary_structure(self):
        """Test that metrics summary has expected structure."""
        state = WorkflowState(jira_key="TEST-123")
        state.status = "SUCCESS"
        state.runbooks = [{"title": "Test 1"}, {"title": "Test 2"}]
        state.add_performance_metric("test_operation", 1.5)
        
        summary = state.get_metrics_summary()
        
        required_keys = ["total_duration", "processing_time", "runbooks_found", "status"]
        for key in required_keys:
            assert key in summary
        
        assert summary["status"] == "SUCCESS"
        assert summary["runbooks_found"] == "2"
        assert "s" in summary["total_duration"] or "ms" in summary["total_duration"]


@pytest.mark.integration
class TestIntegratedPolish:
    """Integration tests for all polish improvements together."""
    
    @pytest.fixture
    def nodes(self):
        """Create nodes instance for integration testing."""
        return DBRunbookFinderNodes(use_real_tools=False)
    
    def test_formatted_metrics_in_console_output(self, nodes, capsys):
        """Test that console output uses formatted metrics."""
        state = WorkflowState(jira_key="INTEGRATION-1")
        state.incident_data = {
            "summary": "Test incident",
            "client": "Test Client",
            "project_key": "TEST",
            "issue_type": "Incident",
            "priority": "Medium",
            "assignee": "Test User",
            "status": "Open",
            "created": "2024-01-01T00:00:00.000Z",
            "labels": []
        }
        
        # Mock the Jira response
        with patch.object(nodes, '_get_mock_jira_response') as mock_jira:
            mock_jira.return_value = {
                "fields": state.incident_data
            }
            
            # Run fetch incident node
            import asyncio
            asyncio.run(nodes.fetch_incident_node(state))
            
            # Capture console output
            captured = capsys.readouterr()
            
            # Check that formatted duration appears in output
            assert "Processing Time:" in captured.out
            # Should have units (s or ms)
            assert ("s" in captured.out or "ms" in captured.out)

    def test_relevance_formatting_consistency(self, nodes):
        """Test that relevance scores are formatted consistently."""
        state = WorkflowState(jira_key="RELEVANCE-1")
        state.runbooks = [
            {"title": "High Relevance", "relevance_score": 0.892, "url": "http://test.com", "space_key": "TEST"},
            {"title": "Medium Relevance", "relevance_score": 0.654, "url": "http://test.com", "space_key": "TEST"},
            {"title": "Low Relevance", "relevance_score": 0.321, "url": "http://test.com", "space_key": "TEST"}
        ]
        
        # Mock Jira client
        with patch('src.tools.jira.app.jira.JiraClient') as mock_jira_class:
            mock_jira_instance = MagicMock()
            mock_jira_class.return_value = mock_jira_instance
            
            # Run update Jira results node
            import asyncio
            asyncio.run(nodes.update_jira_with_results_node(state))
            
            # Verify that add_internal_comment was called
            assert mock_jira_instance.add_internal_comment.called
            
            # Get the comment text
            call_args = mock_jira_instance.add_internal_comment.call_args
            comment_text = call_args[0][1]  # Second argument is the comment text
            
            # Check that relevance scores are formatted as percentages
            assert "89.2%" in comment_text  # High relevance
            assert "65.4%" in comment_text  # Medium relevance
            assert "32.1%" in comment_text  # Low relevance

    def test_accessible_summary_integration(self, nodes):
        """Test accessible summary integration in notify_team_node."""
        state = WorkflowState(jira_key="ACCESS-1")
        state.status = "SUCCESS"
        state.incident_data = {"summary": "Test incident", "client": "Test Client"}
        state.runbooks = [{"title": "Test Runbook", "relevance_score": 0.75}]
        state.add_performance_metric("total", 2.5)
        
        # Test that accessible summary is created
        summary = nodes._create_accessible_summary(state)
        
        assert "Runbook Recommendations Found" in summary
        assert "ACCESS-1" in summary
        assert "1 recommendations found" in summary
        
        # Verify it's concise for notifications
        assert len(summary) < 200


@pytest.mark.performance
class TestPolishPerformance:
    """Performance tests for polish features."""
    
    def test_metrics_formatting_performance(self):
        """Test formatting functions don't add significant overhead."""
        import time
        
        # Test 1000 formatting operations
        durations = [3.14159, 1.23456, 0.98765] * 334  # ~1000 items
        
        start_time = time.time()
        for duration in durations:
            MetricsFormatter.format_duration(duration)
        total_time = time.time() - start_time
        
        assert total_time < 0.01  # Less than 10ms for 1000 operations

    def test_percentage_formatting_performance(self):
        """Test percentage formatting performance."""
        import time
        
        scores = [0.123, 0.456, 0.789, 0.999] * 250  # 1000 items
        
        start_time = time.time()
        for score in scores:
            MetricsFormatter.format_percentage(score)
        total_time = time.time() - start_time
        
        assert total_time < 0.01  # Less than 10ms for 1000 operations

    def test_relevance_enhancement_performance(self):
        """Test relevance enhancement doesn't slow search significantly."""
        from src.tools.confluence.app.vector_store import VectorStore
        
        vector_store = VectorStore(collection_name='test-collection')
        
        # Mock multiple search results
        test_cases = [
            ("database connection", "database connection troubleshooting", 0.6),
            ("performance issues", "performance tuning guide", 0.5),
            ("backup failure", "backup and recovery procedures", 0.7),
        ] * 10  # 30 enhancements
        
        import time
        start_time = time.time()
        
        for query, content, base_score in test_cases:
            vector_store._enhance_relevance_score(query, content, base_score)
        
        processing_time = time.time() - start_time
        
        assert processing_time < 0.05  # Less than 50ms for 30 enhancements

    def test_workflow_state_metrics_performance(self):
        """Test that WorkflowState metrics methods are fast."""
        import time
        
        state = WorkflowState(jira_key="PERF-1")
        
        # Add multiple metrics
        for i in range(100):
            state.add_performance_metric(f"operation_{i}", 0.1 + (i * 0.01))
        
        start_time = time.time()
        
        # Test multiple calls to formatted methods
        for _ in range(100):
            state.get_formatted_duration()
            state.get_metrics_summary()
        
        total_time = time.time() - start_time
        
        assert total_time < 0.01  # Less than 10ms for 100 calls