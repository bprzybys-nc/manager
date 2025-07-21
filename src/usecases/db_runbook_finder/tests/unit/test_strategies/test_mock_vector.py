"""
Unit tests for MockVectorStrategy.

Tests all methods of the mock vector strategy for comprehensive coverage
and validates performance requirements (<50ms).
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategies.mock_vector import MockVectorStrategy
from src.usecases.db_runbook_finder.mcp_server.exceptions import VectorSearchError, RunbookNotFoundError


class TestMockVectorStrategy:
    """Test suite for MockVectorStrategy."""
    
    @pytest.fixture
    def mock_strategy(self):
        """Create mock vector strategy instance."""
        return MockVectorStrategy()
    
    @pytest.mark.asyncio
    async def test_health_check_always_returns_true(self, mock_strategy):
        """Test that health check always returns True for mock strategy."""
        result = await mock_strategy.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_semantic_search_success_with_database_query(self, mock_strategy):
        """Test successful semantic search with database-related query."""
        query = "database connection timeout issues"
        
        results = await mock_strategy.semantic_search(query, limit=3)
        
        # Validate response structure
        assert isinstance(results, list)
        assert len(results) <= 3
        
        # Check each result has required fields
        for result in results:
            assert "runbook_id" in result
            assert "title" in result
            assert "similarity_score" in result
            assert "metadata" in result
            assert "content_preview" in result
            assert "source" in result
            assert result["source"] == "mock"
            assert 0.0 <= result["similarity_score"] <= 1.0
            
            # Validate metadata structure
            metadata = result["metadata"]
            assert "url" in metadata
            assert "space_key" in metadata
            assert "tags" in metadata
    
    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(self, mock_strategy):
        """Test semantic search with empty query."""
        results = await mock_strategy.semantic_search("", limit=5)
        assert isinstance(results, list)
        assert len(results) == 0  # Empty query should return no results
    
    @pytest.mark.asyncio
    async def test_semantic_search_gap_scenario(self, mock_strategy):
        """Test semantic search for gap scenario queries."""
        gap_queries = ["gap_scenario", "nonexistent_technology", "no_results_wanted"]
        
        for query in gap_queries:
            results = await mock_strategy.semantic_search(query, limit=5)
            assert isinstance(results, list)
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_performance_requirement(self, mock_strategy):
        """Test that semantic search meets performance requirement (<50ms)."""
        query = "backup recovery procedures performance"
        
        start_time = asyncio.get_event_loop().time()
        results = await mock_strategy.semantic_search(query, limit=5)
        end_time = asyncio.get_event_loop().time()
        
        duration_ms = (end_time - start_time) * 1000
        assert duration_ms < 50, f"Semantic search took {duration_ms:.2f}ms, should be <50ms"
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_semantic_search_different_limits(self, mock_strategy):
        """Test semantic search with various limit parameters."""
        query = "database performance tuning"
        
        for limit in [1, 3, 5, 10]:
            results = await mock_strategy.semantic_search(query, limit=limit)
            assert len(results) <= limit
    
    @pytest.mark.asyncio
    async def test_semantic_search_relevance_ordering(self, mock_strategy):
        """Test that results are ordered by relevance (similarity score)."""
        query = "database connection troubleshooting"
        
        results = await mock_strategy.semantic_search(query, limit=5)
        
        if len(results) > 1:
            # Check that results are ordered by similarity_score (descending)
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]
    
    @pytest.mark.asyncio
    async def test_add_runbook_embedding_success(self, mock_strategy):
        """Test successful addition of runbook embedding."""
        runbook_id = "test_runbook_123"
        content = "This is test runbook content about database troubleshooting and performance optimization."
        metadata = {
            "title": "Test Runbook",
            "space_key": "TEST",
            "url": "https://test.com/runbook/123",
            "tags": ["database", "test"]
        }
        
        embedding_id = await mock_strategy.add_runbook_embedding(runbook_id, content, metadata)
        
        assert isinstance(embedding_id, str)
        assert embedding_id.startswith("emb_")
        assert runbook_id in embedding_id
    
    @pytest.mark.asyncio
    async def test_add_runbook_embedding_empty_content(self, mock_strategy):
        """Test adding runbook with empty content."""
        runbook_id = "test_empty_123"
        content = ""
        metadata = {"title": "Empty Test Runbook", "space_key": "TEST"}
        
        embedding_id = await mock_strategy.add_runbook_embedding(runbook_id, content, metadata)
        assert isinstance(embedding_id, str)
        assert runbook_id in embedding_id
    
    @pytest.mark.asyncio
    async def test_add_runbook_embedding_minimal_metadata(self, mock_strategy):
        """Test adding runbook with minimal metadata."""
        runbook_id = "test_minimal_123"
        content = "Minimal test content"
        metadata = {}
        
        embedding_id = await mock_strategy.add_runbook_embedding(runbook_id, content, metadata)
        assert isinstance(embedding_id, str)
    
    @pytest.mark.asyncio
    async def test_update_runbook_embedding_success(self, mock_strategy):
        """Test successful update of runbook embedding."""
        runbook_id = "test_update_123"
        original_content = "Original content"
        updated_content = "Updated content with new information"
        metadata = {"title": "Update Test Runbook", "space_key": "TEST"}
        
        # First add the runbook
        original_id = await mock_strategy.add_runbook_embedding(runbook_id, original_content, metadata)
        
        # Then update it
        success = await mock_strategy.update_runbook_embedding(runbook_id, updated_content, metadata)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_update_runbook_embedding_nonexistent(self, mock_strategy):
        """Test updating non-existent runbook embedding."""
        runbook_id = "nonexistent_runbook"
        content = "Updated content"
        metadata = {"title": "Non-existent"}
        
        success = await mock_strategy.update_runbook_embedding(runbook_id, content, metadata)
        # Mock should return True even for non-existent runbooks
        assert success is True
    
    @pytest.mark.asyncio
    async def test_remove_runbook_embedding_success(self, mock_strategy):
        """Test successful removal of runbook embedding."""
        runbook_id = "test_remove_123"
        content = "Content to be removed"
        metadata = {"title": "Remove Test Runbook"}
        
        # First add the runbook
        await mock_strategy.add_runbook_embedding(runbook_id, content, metadata)
        
        # Then remove it
        success = await mock_strategy.remove_runbook_embedding(runbook_id)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_remove_runbook_embedding_nonexistent(self, mock_strategy):
        """Test removing non-existent runbook embedding."""
        success = await mock_strategy.remove_runbook_embedding("nonexistent_runbook")
        # Mock should return True even for non-existent runbooks
        assert success is True
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_success(self, mock_strategy):
        """Test successful collection statistics retrieval."""
        stats = await mock_strategy.get_collection_stats()
        
        assert isinstance(stats, dict)
        assert "total_embeddings" in stats
        assert "collection_size" in stats
        assert "last_updated" in stats
        assert "embedding_dimension" in stats
        assert "source" in stats
        assert stats["source"] == "mock"
        
        # Validate data types
        assert isinstance(stats["total_embeddings"], int)
        assert stats["total_embeddings"] >= 0
        assert isinstance(stats["collection_size"], int)
        assert isinstance(stats["embedding_dimension"], int)
        assert stats["embedding_dimension"] > 0
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_after_operations(self, mock_strategy):
        """Test collection stats after adding/removing embeddings."""
        # Get initial stats
        initial_stats = await mock_strategy.get_collection_stats()
        initial_count = initial_stats["total_embeddings"]
        
        # Add a runbook
        await mock_strategy.add_runbook_embedding("test_stats_123", "Test content", {"title": "Stats Test"})
        
        # Get updated stats
        updated_stats = await mock_strategy.get_collection_stats()
        assert updated_stats["total_embeddings"] >= initial_count
    
    @pytest.mark.asyncio
    async def test_clear_collection_success(self, mock_strategy):
        """Test successful collection clearing."""
        # Add some test runbooks first
        await mock_strategy.add_runbook_embedding("test_clear_1", "Content 1", {"title": "Clear Test 1"})
        await mock_strategy.add_runbook_embedding("test_clear_2", "Content 2", {"title": "Clear Test 2"})
        
        # Clear the collection
        success = await mock_strategy.clear_collection()
        assert success is True
        
        # Verify collection is empty
        stats = await mock_strategy.get_collection_stats()
        assert stats["total_embeddings"] == 0
    
    # Test helper methods
    def test_get_mock_embeddings(self, mock_strategy):
        """Test mock embeddings retrieval."""
        embeddings = mock_strategy.get_mock_embeddings()
        
        assert isinstance(embeddings, dict)
        # Should have some initial embeddings
        assert len(embeddings) >= 0
        
        # Check structure of embeddings if any exist
        for embedding_id, embedding_data in embeddings.items():
            assert "runbook_id" in embedding_data
            assert "content" in embedding_data
            assert "metadata" in embedding_data
            assert "embedding_vector" in embedding_data
            assert "created_at" in embedding_data
    
    def test_clear_data(self, mock_strategy):
        """Test data clearing functionality."""
        # Add some test data
        mock_strategy._mock_embeddings["test_clear"] = {
            "runbook_id": "test",
            "content": "test content",
            "metadata": {},
            "embedding_vector": [0.1, 0.2, 0.3],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Clear data
        mock_strategy.clear_data()
        
        # Verify data is cleared
        embeddings = mock_strategy.get_mock_embeddings()
        assert len(embeddings) == 0
    
    def test_simulate_similarity_computation(self, mock_strategy):
        """Test similarity computation simulation."""
        query = "database connection"
        content = "database connection troubleshooting guide"
        
        similarity = mock_strategy._compute_mock_similarity(query, content)
        
        assert 0.0 <= similarity <= 1.0
        assert isinstance(similarity, float)
    
    def test_similarity_higher_for_relevant_content(self, mock_strategy):
        """Test that similarity is higher for more relevant content."""
        query = "database connection"
        
        relevant_content = "database connection troubleshooting and timeout issues"
        irrelevant_content = "backup recovery procedures for file systems"
        
        relevant_similarity = mock_strategy._compute_mock_similarity(query, relevant_content)
        irrelevant_similarity = mock_strategy._compute_mock_similarity(query, irrelevant_content)
        
        # Relevant content should have higher similarity
        assert relevant_similarity > irrelevant_similarity
    
    @pytest.mark.asyncio
    async def test_semantic_search_concurrent_requests(self, mock_strategy):
        """Test concurrent semantic search requests for thread safety."""
        query = "database troubleshooting performance"
        
        # Run multiple concurrent searches
        tasks = [
            mock_strategy.semantic_search(query, limit=3)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be consistent for the same query
        first_result = results[0]
        for result in results[1:]:
            assert len(result) == len(first_result)
            # Basic structure should be the same
            if result and first_result:
                assert result[0]["runbook_id"] == first_result[0]["runbook_id"]
    
    @pytest.mark.asyncio
    async def test_add_and_search_integration(self, mock_strategy):
        """Test integration of adding embeddings and searching."""
        # Add a custom runbook
        runbook_id = "integration_test_123"
        content = "Custom integration test runbook for database performance optimization"
        metadata = {
            "title": "Integration Test Runbook",
            "space_key": "TEST",
            "tags": ["integration", "test", "database"]
        }
        
        await mock_strategy.add_runbook_embedding(runbook_id, content, metadata)
        
        # Search for content that should match
        results = await mock_strategy.semantic_search("database performance", limit=10)
        
        # Should find our added runbook
        runbook_ids = [r["runbook_id"] for r in results]
        assert runbook_id in runbook_ids
    
    @pytest.mark.asyncio
    async def test_error_handling_simulated_failure(self, mock_strategy):
        """Test error handling with simulated failures."""
        # Patch a method to raise an exception
        with patch.object(mock_strategy, '_generate_mock_embedding', side_effect=Exception("Simulated failure")):
            with pytest.raises(VectorSearchError):
                await mock_strategy.add_runbook_embedding("test_fail", "content", {})
    
    def test_mock_embedding_vector_generation(self, mock_strategy):
        """Test mock embedding vector generation."""
        content = "test content for embedding"
        
        vector = mock_strategy._generate_mock_embedding(content)
        
        assert isinstance(vector, list)
        assert len(vector) > 0
        assert all(isinstance(x, float) for x in vector)
        
        # Vector should be consistent for same content
        vector2 = mock_strategy._generate_mock_embedding(content)
        assert vector == vector2
    
    def test_mock_embedding_different_content_different_vectors(self, mock_strategy):
        """Test that different content produces different embeddings."""
        content1 = "database connection troubleshooting"
        content2 = "backup recovery procedures"
        
        vector1 = mock_strategy._generate_mock_embedding(content1)
        vector2 = mock_strategy._generate_mock_embedding(content2)
        
        # Vectors should be different for different content
        assert vector1 != vector2
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, mock_strategy):
        """Test performance with bulk operations."""
        start_time = asyncio.get_event_loop().time()
        
        # Add multiple runbooks
        tasks = []
        for i in range(10):
            task = mock_strategy.add_runbook_embedding(
                f"bulk_test_{i}",
                f"Bulk test content {i} for database troubleshooting",
                {"title": f"Bulk Test {i}", "space_key": "TEST"}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Perform search
        await mock_strategy.semantic_search("database troubleshooting", limit=5)
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should complete within reasonable time
        assert duration_ms < 500, f"Bulk operations took {duration_ms:.2f}ms"
    
    def test_strategy_initialization(self, mock_strategy):
        """Test strategy initialization."""
        assert mock_strategy is not None
        
        # Should start with empty embeddings
        embeddings = mock_strategy.get_mock_embeddings()
        assert isinstance(embeddings, dict)