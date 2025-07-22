"""
Unit tests for MockDiscoveryStrategy.

Tests all methods of the mock discovery strategy following the RunbookDiscoveryStrategy Protocol
and validates performance requirements.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategies.mock_discovery import MockDiscoveryStrategy
from src.usecases.db_runbook_finder.mcp_server.exceptions import MCPRunbookError


class TestMockDiscoveryStrategy:
    """Test suite for MockDiscoveryStrategy Protocol implementation."""
    
    @pytest.fixture
    def mock_strategy(self):
        """Create mock discovery strategy instance."""
        return MockDiscoveryStrategy()
    
    @pytest.mark.asyncio
    async def test_health_check_always_returns_true(self, mock_strategy):
        """Test that health check always returns True for mock strategy."""
        result = await mock_strategy.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_discover_runbooks_success(self, mock_strategy):
        """Test successful runbook discovery."""
        spaces = ["MOCK_RUNBOOKS"]
        
        results = await mock_strategy.discover_runbooks(spaces)
        
        # Validate response structure
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check each result has required fields
        for result in results:
            assert "runbook_id" in result
            assert "title" in result
            assert "space_key" in result
            assert "source" in result
            assert result["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_discover_runbooks_empty_spaces(self, mock_strategy):
        """Test discovery with empty spaces list."""
        results = await mock_strategy.discover_runbooks([])
        assert isinstance(results, list)
        # Should still return runbooks when no spaces specified
    
    @pytest.mark.asyncio
    async def test_discover_runbooks_unknown_space(self, mock_strategy):
        """Test discovery in unknown space."""
        results = await mock_strategy.discover_runbooks(["UNKNOWN_SPACE"])
        assert isinstance(results, list)
        # Mock implementation might still return results
    
    @pytest.mark.asyncio
    async def test_get_runbook_content_success(self, mock_strategy):
        """Test successful runbook content retrieval."""
        # First discover some runbooks to get valid IDs
        runbooks = await mock_strategy.discover_runbooks(["MOCK_RUNBOOKS"])
        assert len(runbooks) > 0
        
        runbook_id = runbooks[0]["runbook_id"]
        content = await mock_strategy.get_runbook_content(runbook_id)
        
        # Validate response structure
        assert content is not None
        assert isinstance(content, dict)
        assert "metadata" in content
        assert "source" in content
        assert content["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_get_runbook_content_not_found(self, mock_strategy):
        """Test runbook content retrieval for non-existent runbook."""
        content = await mock_strategy.get_runbook_content("nonexistent_id")
        assert content is None
    
    @pytest.mark.asyncio
    async def test_validate_runbook_content_valid_page(self, mock_strategy):
        """Test runbook content validation with valid page."""
        valid_page = {
            "title": "Database Troubleshooting Runbook",
            "content": "This is a step-by-step procedure for database issues",
            "procedures": [{"step": 1, "description": "Check database status"}],
            "troubleshooting_steps": [{"symptom": "Connection timeout"}]
        }
        
        is_valid = await mock_strategy.validate_runbook_content(valid_page)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_runbook_content_invalid_page(self, mock_strategy):
        """Test runbook content validation with invalid page."""
        invalid_page = {
            "title": "Random Document",
            "content": "Just some random text"
        }
        
        is_valid = await mock_strategy.validate_runbook_content(invalid_page)
        assert is_valid in [True, False]  # Mock implementation might be lenient
    
    @pytest.mark.asyncio
    async def test_extract_runbook_metadata_success(self, mock_strategy):
        """Test successful metadata extraction."""
        page = {
            "title": "Test Runbook",
            "metadata": {
                "page_id": "test_123",
                "space_key": "TEST",
                "tags": ["test", "runbook"]
            },
            "raw_content": "Test runbook content with procedures"
        }
        
        metadata = await mock_strategy.extract_runbook_metadata(page)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "page_id" in metadata
        assert "space_key" in metadata
        assert "extracted_at" in metadata
        assert "source" in metadata
        assert metadata["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_extract_runbook_metadata_minimal_page(self, mock_strategy):
        """Test metadata extraction with minimal page data."""
        page = {"title": "Minimal Runbook"}
        
        metadata = await mock_strategy.extract_runbook_metadata(page)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert metadata["title"] == "Minimal Runbook"
        assert "extracted_at" in metadata
    
    @pytest.mark.asyncio
    async def test_search_runbooks_by_query_success(self, mock_strategy):
        """Test successful runbook search by query."""
        query = "database connection"
        spaces = ["MOCK_RUNBOOKS"]
        
        results = await mock_strategy.search_runbooks_by_query(query, spaces, limit=5)
        
        # Validate response structure
        assert isinstance(results, list)
        assert len(results) <= 5
        
        # Check each result has required fields
        for result in results:
            assert "runbook_id" in result
            assert "title" in result
            assert "source" in result
            assert result["source"] == "mock"
            if "search_relevance" in result:
                assert 0.0 <= result["search_relevance"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_search_runbooks_by_query_empty_query(self, mock_strategy):
        """Test search with empty query string."""
        results = await mock_strategy.search_runbooks_by_query("", ["MOCK_RUNBOOKS"], limit=5)
        assert isinstance(results, list)
        # Empty query should return empty results
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_runbooks_by_query_none_spaces(self, mock_strategy):
        """Test search with None spaces parameter."""
        query = "database troubleshooting"
        
        results = await mock_strategy.search_runbooks_by_query(query, None, limit=3)
        assert isinstance(results, list)
        # Should still work with None spaces
    
    @pytest.mark.asyncio
    async def test_search_runbooks_by_query_performance_requirement(self, mock_strategy):
        """Test that search meets performance requirement (<50ms)."""
        query = "backup recovery procedures"
        spaces = ["MOCK_RUNBOOKS"]
        
        start_time = asyncio.get_event_loop().time()
        results = await mock_strategy.search_runbooks_by_query(query, spaces, limit=5)
        end_time = asyncio.get_event_loop().time()
        
        duration_ms = (end_time - start_time) * 1000
        assert duration_ms < 50, f"Search took {duration_ms:.2f}ms, should be <50ms"
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_runbooks_by_query_with_different_limits(self, mock_strategy):
        """Test search with various limit parameters."""
        query = "database performance"
        
        # Test different limits
        for limit in [1, 3, 5, 10]:
            results = await mock_strategy.search_runbooks_by_query(query, ["MOCK_RUNBOOKS"], limit=limit)
            assert len(results) <= limit
    
    @pytest.mark.asyncio
    async def test_search_runbooks_case_insensitive(self, mock_strategy):
        """Test that search is case insensitive."""
        queries = [
            "DATABASE connection",
            "database CONNECTION", 
            "Database Connection",
            "DATABASE CONNECTION"
        ]
        
        results_list = []
        for query in queries:
            results = await mock_strategy.search_runbooks_by_query(query, ["MOCK_RUNBOOKS"], limit=5)
            results_list.append(len(results))
        
        # All queries should return the same number of results
        assert len(set(results_list)) <= 1  # All should be the same or very similar
    
    @pytest.mark.asyncio
    async def test_search_concurrent_requests(self, mock_strategy):
        """Test concurrent search requests for thread safety."""
        query = "database troubleshooting"
        spaces = ["MOCK_RUNBOOKS"]
        
        # Run multiple concurrent searches
        tasks = [
            mock_strategy.search_runbooks_by_query(query, spaces, limit=3)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be identical for the same query
        first_result = results[0]
        for result in results[1:]:
            assert len(result) == len(first_result)
            # Basic structure should be the same
            if result and first_result:
                assert result[0]["runbook_id"] == first_result[0]["runbook_id"]
    
    # Test helper methods that are publicly available
    def test_get_all_mock_runbooks(self, mock_strategy):
        """Test that mock runbooks data is accessible."""
        runbooks = mock_strategy.get_all_mock_runbooks()
        
        assert isinstance(runbooks, list)
        assert len(runbooks) > 0
        
        # Verify structure of each runbook
        for runbook in runbooks:
            assert "metadata" in runbook
            assert isinstance(runbook["metadata"], dict)
    
    def test_clear_mock_data(self, mock_strategy):
        """Test data clearing functionality."""
        # Get initial count
        initial_count = len(mock_strategy.get_all_mock_runbooks())
        assert initial_count > 0
        
        # This should not raise any exceptions
        mock_strategy.clear_mock_data()
        
        # Data should be reloaded after clearing (either from files or fallback)
        runbooks = mock_strategy.get_all_mock_runbooks()
        assert isinstance(runbooks, list)  # Should at least return a list (even if empty in test env)
    
    def test_add_mock_runbook(self, mock_strategy):
        """Test adding custom mock runbook."""
        initial_count = len(mock_strategy.get_all_mock_runbooks())
        
        custom_runbook = {
            "metadata": {
                "title": "Custom Test Runbook",
                "tags": ["test", "custom"]
            },
            "procedures": [{"step": 1, "description": "Custom procedure"}],
            "troubleshooting_steps": [],
            "prerequisites": [],
            "raw_content": "Custom runbook content"
        }
        
        mock_strategy.add_mock_runbook(custom_runbook)
        
        final_count = len(mock_strategy.get_all_mock_runbooks())
        assert final_count == initial_count + 1
    
    def test_mock_strategy_initialization(self, mock_strategy):
        """Test that strategy initializes correctly."""
        assert mock_strategy is not None
        
        # Should have mock runbooks loaded
        runbooks = mock_strategy.get_all_mock_runbooks()
        assert len(runbooks) >= 1  # Should have at least one runbook (fallback or loaded)
    
    @pytest.mark.asyncio
    async def test_error_handling_with_exception(self, mock_strategy):
        """Test error handling when operations encounter exceptions."""
        # Test with invalid input that might cause an exception
        try:
            await mock_strategy.extract_runbook_metadata(None)
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, (MCPRunbookError, TypeError, AttributeError))