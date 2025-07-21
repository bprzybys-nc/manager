"""
Unit tests for MockDiscoveryStrategy.

Tests all methods of the mock discovery strategy for comprehensive coverage
and validates performance requirements.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategies.mock_discovery import MockDiscoveryStrategy
from src.usecases.db_runbook_finder.mcp_server.exceptions import RunbookNotFoundError, RunbookDiscoveryError


class TestMockDiscoveryStrategy:
    """Test suite for MockDiscoveryStrategy."""
    
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
    async def test_search_runbooks_success_with_database_query(self, mock_strategy):
        """Test successful runbook search with database-related query."""
        query = "database connection timeout troubleshooting"
        spaces = ["AAVA", "MCDBA"]
        
        results = await mock_strategy.search_runbooks(query, spaces, limit=3)
        
        # Validate response structure
        assert isinstance(results, list)
        assert len(results) <= 3
        
        # Check each result has required fields
        for result in results:
            assert "runbook_id" in result
            assert "title" in result
            assert "url" in result
            assert "space_key" in result
            assert "search_relevance" in result
            assert "description" in result
            assert "last_modified" in result
            assert "source" in result
            assert result["source"] == "mock"
            assert 0.0 <= result["search_relevance"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_search_runbooks_empty_results_for_gap_query(self, mock_strategy):
        """Test empty results for gap scenario queries."""
        # Test queries that should return empty results
        gap_queries = ["gap_scenario", "nonexistent_topic", "no_results_please"]
        
        for query in gap_queries:
            results = await mock_strategy.search_runbooks(query, ["AAVA"], limit=5)
            assert isinstance(results, list)
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_runbooks_with_different_limits(self, mock_strategy):
        """Test search with various limit parameters."""
        query = "database performance"
        
        # Test different limits
        for limit in [1, 3, 5, 10]:
            results = await mock_strategy.search_runbooks(query, ["MCDBA"], limit=limit)
            assert len(results) <= limit
    
    @pytest.mark.asyncio
    async def test_search_runbooks_with_empty_query(self, mock_strategy):
        """Test search with empty query string."""
        results = await mock_strategy.search_runbooks("", ["AAVA"], limit=5)
        assert isinstance(results, list)
        # Empty query should return empty results
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_runbooks_with_none_spaces(self, mock_strategy):
        """Test search with None spaces parameter."""
        query = "database troubleshooting"
        
        results = await mock_strategy.search_runbooks(query, None, limit=3)
        assert isinstance(results, list)
        # Should still work with None spaces
    
    @pytest.mark.asyncio
    async def test_search_runbooks_performance_requirement(self, mock_strategy):
        """Test that search meets performance requirement (<50ms)."""
        query = "backup recovery procedures"
        spaces = ["AAVA", "MCDBA"]
        
        start_time = asyncio.get_event_loop().time()
        results = await mock_strategy.search_runbooks(query, spaces, limit=5)
        end_time = asyncio.get_event_loop().time()
        
        duration_ms = (end_time - start_time) * 1000
        assert duration_ms < 50, f"Search took {duration_ms:.2f}ms, should be <50ms"
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_get_runbook_details_success(self, mock_strategy):
        """Test successful runbook details retrieval."""
        runbook_id = "123456"  # Database connection troubleshooting
        
        details = await mock_strategy.get_runbook_details(runbook_id)
        
        # Validate response structure
        assert isinstance(details, dict)
        assert details["runbook_id"] == runbook_id
        assert "title" in details
        assert "description" in details
        assert "content" in details
        assert "metadata" in details
        assert "procedures" in details
        assert "troubleshooting_steps" in details
        assert "prerequisites" in details
        assert details["source"] == "mock"
        
        # Validate metadata structure
        metadata = details["metadata"]
        assert "space_key" in metadata
        assert "page_id" in metadata
        assert "url" in metadata
        assert "last_modified" in metadata
        assert "tags" in metadata
    
    @pytest.mark.asyncio
    async def test_get_runbook_details_not_found(self, mock_strategy):
        """Test runbook details retrieval for non-existent runbook."""
        with pytest.raises(RunbookNotFoundError) as exc_info:
            await mock_strategy.get_runbook_details("nonexistent_id")
        
        assert "nonexistent_id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_runbook_details_with_known_runbooks(self, mock_strategy):
        """Test details retrieval for all known mock runbooks."""
        known_runbook_ids = ["123456", "234567", "345678", "456789", "567890"]
        
        for runbook_id in known_runbook_ids:
            details = await mock_strategy.get_runbook_details(runbook_id)
            assert details["runbook_id"] == runbook_id
            assert details["title"]  # Should have non-empty title
            assert details["content"]["procedures"]  # Should have procedures
    
    @pytest.mark.asyncio
    async def test_validate_runbook_access_success(self, mock_strategy):
        """Test successful runbook access validation."""
        runbook_id = "123456"
        user_context = {"user": "test_user@company.com", "permissions": ["read"]}
        
        is_accessible = await mock_strategy.validate_runbook_access(runbook_id, user_context)
        assert is_accessible is True
    
    @pytest.mark.asyncio
    async def test_validate_runbook_access_nonexistent_runbook(self, mock_strategy):
        """Test access validation for non-existent runbook."""
        runbook_id = "nonexistent_id"
        user_context = {"user": "test_user@company.com"}
        
        is_accessible = await mock_strategy.validate_runbook_access(runbook_id, user_context)
        assert is_accessible is False
    
    @pytest.mark.asyncio
    async def test_validate_runbook_access_no_user_context(self, mock_strategy):
        """Test access validation without user context."""
        runbook_id = "123456"
        
        # Should work with empty context in mock implementation
        is_accessible = await mock_strategy.validate_runbook_access(runbook_id, {})
        assert is_accessible is True
    
    @pytest.mark.asyncio
    async def test_validate_runbook_access_none_context(self, mock_strategy):
        """Test access validation with None user context."""
        runbook_id = "123456"
        
        is_accessible = await mock_strategy.validate_runbook_access(runbook_id, None)
        assert is_accessible is True
    
    @pytest.mark.asyncio
    async def test_get_runbook_categories_success(self, mock_strategy):
        """Test successful runbook categories retrieval."""
        runbook_id = "123456"
        
        categories = await mock_strategy.get_runbook_categories(runbook_id)
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        # Should contain relevant categories for database connection runbook
        expected_categories = ["database", "troubleshooting", "connection"]
        for category in expected_categories:
            assert category in categories
    
    @pytest.mark.asyncio 
    async def test_get_runbook_categories_not_found(self, mock_strategy):
        """Test categories retrieval for non-existent runbook."""
        with pytest.raises(RunbookNotFoundError):
            await mock_strategy.get_runbook_categories("nonexistent_id")
    
    @pytest.mark.asyncio
    async def test_get_runbook_categories_all_known_runbooks(self, mock_strategy):
        """Test categories for all known runbooks."""
        known_runbook_ids = ["123456", "234567", "345678", "456789", "567890"]
        
        for runbook_id in known_runbook_ids:
            categories = await mock_strategy.get_runbook_categories(runbook_id)
            assert isinstance(categories, list)
            assert len(categories) >= 2  # Each should have at least 2 categories
    
    # Test helper methods
    def test_get_mock_runbooks_data(self, mock_strategy):
        """Test that mock runbooks data is properly accessible."""
        runbooks = mock_strategy.get_mock_runbooks()
        
        assert isinstance(runbooks, dict)
        assert len(runbooks) > 0
        
        # Verify structure of each runbook
        for runbook_id, runbook_data in runbooks.items():
            assert "title" in runbook_data
            assert "metadata" in runbook_data
            assert "procedures" in runbook_data
            assert "troubleshooting_steps" in runbook_data
    
    def test_clear_data(self, mock_strategy):
        """Test data clearing functionality."""
        # This should not raise any exceptions
        mock_strategy.clear_data()
        
        # Mock runbooks should still be available after clearing
        runbooks = mock_strategy.get_mock_runbooks()
        assert len(runbooks) > 0
    
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
            results = await mock_strategy.search_runbooks(query, ["AAVA"], limit=5)
            results_list.append(len(results))
        
        # All queries should return the same number of results
        assert len(set(results_list)) <= 1  # All should be the same or very similar
    
    @pytest.mark.asyncio
    async def test_search_runbooks_partial_matches(self, mock_strategy):
        """Test search with partial keyword matches."""
        # Test partial matches
        partial_queries = [
            "database",  # Should match "database connection"
            "connect",   # Should match "connection" 
            "perform",   # Should match "performance"
            "backup"     # Should match "backup recovery"
        ]
        
        for query in partial_queries:
            results = await mock_strategy.search_runbooks(query, ["AAVA", "MCDBA"], limit=5)
            assert isinstance(results, list)
            # At least some queries should return results
    
    @pytest.mark.asyncio
    async def test_search_concurrent_requests(self, mock_strategy):
        """Test concurrent search requests for thread safety."""
        query = "database troubleshooting"
        spaces = ["AAVA", "MCDBA"]
        
        # Run multiple concurrent searches
        tasks = [
            mock_strategy.search_runbooks(query, spaces, limit=3)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be identical for the same query
        first_result = results[0]
        for result in results[1:]:
            assert len(result) == len(first_result)
            # Basic structure should be the same
            if result and first_result:
                assert result[0]["runbook_id"] == first_result[0]["runbook_id"]
    
    def test_mock_strategy_initialization(self, mock_strategy):
        """Test that strategy initializes correctly."""
        assert mock_strategy is not None
        
        # Should have mock runbooks loaded
        runbooks = mock_strategy.get_mock_runbooks()
        assert len(runbooks) >= 5  # Should have at least our known test runbooks
    
    @pytest.mark.asyncio
    async def test_error_handling_with_simulated_failure(self, mock_strategy):
        """Test error handling when operations fail."""
        # Patch a method to raise an exception
        with patch.object(mock_strategy, '_load_runbook_data', side_effect=Exception("Simulated failure")):
            with pytest.raises(RunbookDiscoveryError):
                await mock_strategy.get_runbook_details("123456")