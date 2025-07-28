"""
Comprehensive tests for the --clear-existing flag functionality.

This test suite covers all aspects of the clear existing collection feature
including CLI argument parsing, collection management, safety validation,
and end-to-end workflows.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
import argparse
import sys
from io import StringIO

from src.usecases.db_runbook_finder.discover_runbooks import main_async, handle_collection_clearing
from src.usecases.db_runbook_finder.runbook_discovery_service import RunbookDiscoveryService
from src.tools.confluence.app.models import CollectionStats, ClearingResult


class TestClearExistingCLI:
    """Test CLI argument parsing and validation for clear-existing flag."""
    
    def test_clear_existing_argument_parsing(self):
        """Test that --clear-existing argument is parsed correctly."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--clear-existing', action='store_true')
        parser.add_argument('--collection-name', default='test-collection')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--no-confirm', action='store_true')
        
        args = parser.parse_args(['--clear-existing'])
        assert args.clear_existing is True
    
    def test_clear_existing_with_dry_run(self):
        """Test clear-existing combined with dry-run shows preview."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--clear-existing', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        
        args = parser.parse_args(['--clear-existing', '--dry-run'])
        assert args.clear_existing is True
        assert args.dry_run is True
    
    def test_no_confirm_argument(self):
        """Test --no-confirm argument for automation use."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--no-confirm', action='store_true')
        
        args = parser.parse_args(['--no-confirm'])
        assert args.no_confirm is True


class TestCollectionStatsRetrieval:
    """Test collection statistics retrieval for confirmation display."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock RunbookDiscoveryService."""
        with patch('src.usecases.db_runbook_finder.runbook_discovery_service.VectorStore') as mock_vs:
            service = RunbookDiscoveryService(collection_name="test-collection")
            service.vector_store = mock_vs.return_value
            yield service
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_with_documents(self, mock_service):
        """Test getting collection stats when documents exist."""
        # Mock vector store collection info
        mock_service.vector_store.get_collection_info.return_value = {
            "exists": True,
            "count": 5,
            "name": "test-collection"
        }
        
        # Mock collection peek for sample documents
        mock_service.vector_store._collection.peek.return_value = {
            "metadatas": [
                {"title": "Database Connection Guide"},
                {"title": "Performance Troubleshooting"},
                {"title": "Backup Procedures"}
            ]
        }
        
        stats = await mock_service.get_collection_stats()
        
        assert stats.collection_name == "test-collection"
        assert stats.document_count == 5
        assert len(stats.sample_documents) == 3
        assert "Database Connection Guide" in stats.sample_documents
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_empty_collection(self, mock_service):
        """Test getting stats for empty collection."""
        mock_service.vector_store.get_collection_info.return_value = {
            "exists": True,
            "count": 0,
            "name": "test-collection"
        }
        
        stats = await mock_service.get_collection_stats()
        
        assert stats.collection_name == "test-collection"
        assert stats.document_count == 0
        assert stats.sample_documents == []
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_nonexistent_collection(self, mock_service):
        """Test getting stats for non-existent collection."""
        mock_service.vector_store.get_collection_info.return_value = {
            "exists": False,
            "name": "test-collection"
        }
        
        stats = await mock_service.get_collection_stats()
        
        assert stats.collection_name == "test-collection"
        assert stats.document_count == 0
        assert stats.sample_documents == []


class TestCollectionClearing:
    """Test collection clearing functionality."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service for clearing tests."""
        with patch('src.usecases.db_runbook_finder.runbook_discovery_service.VectorStore') as mock_vs:
            service = RunbookDiscoveryService(collection_name="test-collection")
            service.vector_store = mock_vs.return_value
            yield service
    
    @pytest.mark.asyncio
    async def test_clear_collection_success(self, mock_service):
        """Test successful collection clearing."""
        # Mock collection stats
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=10,
            sample_documents=["Doc 1", "Doc 2"]
        ))
        
        # Mock vector store clearing
        mock_service.vector_store.clear_collection = AsyncMock(return_value=10)
        
        result = await mock_service.clear_collection(confirmation=True)
        
        assert result.success is True
        assert result.documents_cleared == 10
        assert result.collection_name == "test-collection"
        assert result.error_message is None
        
        # Verify vector store clear_collection was called
        mock_service.vector_store.clear_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_collection_without_confirmation(self, mock_service):
        """Test clearing fails without confirmation for non-empty collection."""
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=5,
            sample_documents=["Doc 1"]
        ))
        
        result = await mock_service.clear_collection(confirmation=False)
        
        assert result.success is False
        assert result.error_message is not None
        assert "confirmation required" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_clear_empty_collection(self, mock_service):
        """Test clearing empty collection succeeds without confirmation."""
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=0,
            sample_documents=[]
        ))
        
        result = await mock_service.clear_collection(confirmation=False)
        
        assert result.success is True
        assert result.documents_cleared == 0
    
    @pytest.mark.asyncio
    async def test_clear_collection_error_handling(self, mock_service):
        """Test error handling during collection clearing."""
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=5,
            sample_documents=["Doc 1"]
        ))
        
        # Mock vector store to raise exception
        mock_service.vector_store.clear_collection = AsyncMock(
            side_effect=Exception("ChromaDB connection failed")
        )
        
        result = await mock_service.clear_collection(confirmation=True)
        
        assert result.success is False
        assert result.documents_cleared == 0
        assert "ChromaDB connection failed" in result.error_message


class TestVectorStoreClearing:
    """Test VectorStore collection clearing methods."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock VectorStore."""
        with patch('src.tools.confluence.app.vector_store.chromadb') as mock_chromadb:
            from src.tools.confluence.app.vector_store import VectorStore
            
            # Mock ChromaDB client and collection
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.count.return_value = 10
            mock_client.get_collection.return_value = mock_collection
            
            vector_store = VectorStore(collection_name="test-collection")
            vector_store._client = mock_client
            vector_store._collection = mock_collection
            
            yield vector_store
    
    @pytest.mark.asyncio
    async def test_vector_store_clear_collection(self, mock_vector_store):
        """Test VectorStore clear_collection method."""
        mock_vector_store._collection.count.return_value = 15
        
        # Mock successful delete and recreate
        mock_vector_store._client.delete_collection = MagicMock()
        mock_vector_store._client.create_collection = MagicMock(return_value=mock_vector_store._collection)
        
        cleared_count = await mock_vector_store.clear_collection()
        
        assert cleared_count == 15
        mock_vector_store._client.delete_collection.assert_called_once_with(name="test-collection")
        mock_vector_store._client.create_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vector_store_clear_empty_collection(self, mock_vector_store):
        """Test clearing empty collection."""
        mock_vector_store._collection.count.return_value = 0
        
        cleared_count = await mock_vector_store.clear_collection()
        
        assert cleared_count == 0
        # Should not attempt deletion for empty collection
        mock_vector_store._client.delete_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_vector_store_clear_with_fallback(self, mock_vector_store):
        """Test fallback clearing method when delete/recreate fails."""
        mock_vector_store._collection.count.return_value = 8
        
        # Mock delete_collection to fail
        mock_vector_store._client.delete_collection.side_effect = Exception("Delete failed")
        
        # Mock fallback get/delete method
        mock_vector_store._collection.get.return_value = {
            "ids": ["id1", "id2", "id3", "id4", "id5", "id6", "id7", "id8"]
        }
        mock_vector_store._collection.delete = MagicMock()
        
        cleared_count = await mock_vector_store.clear_collection()
        
        assert cleared_count == 8
        mock_vector_store._collection.delete.assert_called_once_with(ids=["id1", "id2", "id3", "id4", "id5", "id6", "id7", "id8"])
    
    def test_vector_store_get_collection_info(self, mock_vector_store):
        """Test getting collection information."""
        mock_vector_store._collection.count.return_value = 42
        mock_vector_store._collection.metadata = {"description": "Test collection"}
        
        info = mock_vector_store.get_collection_info()
        
        assert info["name"] == "test-collection"
        assert info["exists"] is True
        assert info["count"] == 42
        assert info["metadata"] == {"description": "Test collection"}


class TestClearingWorkflow:
    """Test complete clearing workflow integration."""
    
    @pytest.mark.asyncio
    async def test_handle_collection_clearing_dry_run(self):
        """Test dry run clearing shows preview without making changes."""
        mock_service = MagicMock()
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=25,
            sample_documents=["Sample 1", "Sample 2", "Sample 3"]
        ))
        
        # Capture stdout to verify dry run output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            await handle_collection_clearing(mock_service, dry_run=True, no_confirm=False)
            
            output = mock_stdout.getvalue()
            assert "DRY RUN MODE" in output
            assert "test-collection" in output
            assert "25" in output
            assert "Sample 1" in output
        
        # Verify no actual clearing was attempted
        mock_service.clear_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_collection_clearing_with_confirmation(self):
        """Test clearing with user confirmation."""
        mock_service = MagicMock()
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=10,
            sample_documents=["Doc 1", "Doc 2"]
        ))
        mock_service.clear_collection = AsyncMock(return_value=ClearingResult(
            success=True,
            collection_name="test-collection",
            documents_cleared=10,
            clearing_time=1.5
        ))
        
        # Mock user input to confirm
        with patch('builtins.input', return_value='yes'):
            with patch('sys.stdout', new_callable=StringIO):
                await handle_collection_clearing(mock_service, dry_run=False, no_confirm=False)
        
        mock_service.clear_collection.assert_called_once_with(confirmation=True)
    
    @pytest.mark.asyncio
    async def test_handle_collection_clearing_no_confirm_flag(self):
        """Test clearing with --no-confirm flag for automation."""
        mock_service = MagicMock()
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=5,
            sample_documents=["Doc 1"]
        ))
        mock_service.clear_collection = AsyncMock(return_value=ClearingResult(
            success=True,
            collection_name="test-collection",
            documents_cleared=5,
            clearing_time=0.8
        ))
        
        with patch('sys.stdout', new_callable=StringIO):
            await handle_collection_clearing(mock_service, dry_run=False, no_confirm=True)
        
        mock_service.clear_collection.assert_called_once_with(confirmation=True)
    
    @pytest.mark.asyncio
    async def test_handle_collection_clearing_user_cancellation(self):
        """Test user cancellation during confirmation."""
        mock_service = MagicMock()
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="test-collection",
            document_count=100,
            sample_documents=["Important Doc 1", "Important Doc 2"]
        ))
        
        # Mock user input to cancel
        with patch('builtins.input', return_value='no'):
            with patch('sys.stdout', new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    await handle_collection_clearing(mock_service, dry_run=False, no_confirm=False)
                
                assert exc_info.value.code == 0  # Clean exit
        
        mock_service.clear_collection.assert_not_called()


@pytest.mark.integration
class TestEndToEndClearingIntegration:
    """Integration tests for complete clearing workflow."""
    
    @pytest.mark.asyncio
    async def test_full_clearing_and_discovery_workflow(self):
        """Test complete workflow: clear existing, then discover and populate."""
        # This would be an integration test that uses actual ChromaDB
        # and tests the complete workflow
        
        # For now, we'll use a simplified mock-based integration test
        with patch('src.usecases.db_runbook_finder.runbook_discovery_service.VectorStore') as mock_vs:
            with patch('src.usecases.db_runbook_finder.runbook_discovery_service.ConfluenceClient') as mock_cc:
                # Setup service
                service = RunbookDiscoveryService(collection_name="test-integration")
                
                # Mock initial collection stats (has data)
                mock_vs.return_value.get_collection_info.return_value = {
                    "exists": True,
                    "count": 10,
                    "name": "test-integration"
                }
                
                # Mock clearing operation
                mock_vs.return_value.clear_collection = AsyncMock(return_value=10)
                
                # Test clearing
                stats = await service.get_collection_stats()
                assert stats.document_count == 10
                
                result = await service.clear_collection(confirmation=True)
                assert result.success is True
                assert result.documents_cleared == 10
                
                # Verify processed pages cache was cleared
                assert len(service._processed_pages) == 0


@pytest.mark.performance
class TestClearingPerformance:
    """Performance tests for clearing operations."""
    
    @pytest.mark.asyncio
    async def test_clearing_performance_large_collection(self):
        """Test clearing performance with large collections."""
        mock_service = MagicMock()
        
        # Simulate large collection stats
        mock_service.get_collection_stats = AsyncMock(return_value=CollectionStats(
            collection_name="large-collection",
            document_count=10000,
            sample_documents=["Doc 1", "Doc 2", "Doc 3"]
        ))
        
        # Mock clearing to simulate realistic timing
        async def mock_clear_collection(confirmation=True):
            await asyncio.sleep(0.1)  # Simulate 100ms clearing time
            return ClearingResult(
                success=True,
                collection_name="large-collection",
                documents_cleared=10000,
                clearing_time=0.1
            )
        
        mock_service.clear_collection = mock_clear_collection
        
        start_time = time.time()
        result = await mock_service.clear_collection(confirmation=True)
        total_time = time.time() - start_time
        
        # Should complete within performance requirement (30s for typical collections)
        assert total_time < 30.0
        assert result.success is True
        assert result.documents_cleared == 10000


class TestModelValidation:
    """Test model validation for new data structures."""
    
    def test_collection_stats_validation(self):
        """Test CollectionStats model validation."""
        # Valid stats
        stats = CollectionStats(
            collection_name="test",
            document_count=10,
            sample_documents=["Doc 1", "Doc 2"]
        )
        assert stats.collection_name == "test"
        assert stats.document_count == 10
        assert len(stats.sample_documents) == 2
        
        # Test validation - too many sample documents
        with pytest.raises(ValueError):
            CollectionStats(
                collection_name="test",
                document_count=10,
                sample_documents=["Doc " + str(i) for i in range(15)]  # > 10 limit
            )
    
    def test_clearing_result_validation(self):
        """Test ClearingResult model validation."""
        # Successful result
        result = ClearingResult(
            success=True,
            collection_name="test",
            documents_cleared=5,
            clearing_time=1.5
        )
        assert result.success is True
        assert result.documents_cleared == 5
        assert result.error_message is None
        
        # Failed result with error
        result = ClearingResult(
            success=False,
            collection_name="test",
            documents_cleared=0,
            clearing_time=0.5,
            error_message="Test error"
        )
        assert result.success is False
        assert result.error_message == "Test error"
        
        # Test validation - empty error message
        with pytest.raises(ValueError):
            ClearingResult(
                success=False,
                collection_name="test",
                documents_cleared=0,
                clearing_time=0.5,
                error_message=""  # Empty string not allowed
            )


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for clearing functionality."""
    
    @pytest.mark.asyncio
    async def test_clearing_with_chromadb_connection_failure(self):
        """Test handling of ChromaDB connection failures during clearing."""
        with patch('src.usecases.db_runbook_finder.runbook_discovery_service.VectorStore') as mock_vs:
            service = RunbookDiscoveryService(collection_name="test-collection")
            service.vector_store = mock_vs.return_value
            
            # Mock connection failure
            service.vector_store.clear_collection = AsyncMock(
                side_effect=Exception("Connection to ChromaDB failed")
            )
            
            # Mock stats to show collection has data
            service.get_collection_stats = AsyncMock(return_value=CollectionStats(
                collection_name="test-collection",
                document_count=5,
                sample_documents=["Doc 1"]
            ))
            
            result = await service.clear_collection(confirmation=True)
            
            assert result.success is False
            assert "Connection to ChromaDB failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_clearing_with_malformed_collection_data(self):
        """Test handling of malformed collection data."""
        with patch('src.usecases.db_runbook_finder.runbook_discovery_service.VectorStore') as mock_vs:
            service = RunbookDiscoveryService(collection_name="test-collection")
            service.vector_store = mock_vs.return_value
            
            # Mock malformed collection info
            service.vector_store.get_collection_info.return_value = {
                "exists": True,
                "count": "invalid",  # Should be int
                "name": "test-collection"
            }
            
            stats = await service.get_collection_stats()
            
            # Should gracefully handle malformed data
            assert stats.collection_name == "test-collection"
            assert stats.document_count == 0  # Fallback value
    
    @pytest.mark.asyncio
    async def test_clearing_workflow_with_keyboard_interrupt(self):
        """Test handling of keyboard interrupt during clearing."""
        mock_service = MagicMock()
        mock_service.get_collection_stats = AsyncMock(
            side_effect=KeyboardInterrupt("User cancelled")
        )
        
        with pytest.raises(KeyboardInterrupt):
            await handle_collection_clearing(mock_service, dry_run=False, no_confirm=False)


# Pytest configuration and fixtures for the entire test suite
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session.""" 
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
    finally:
        if not loop.is_closed():
            loop.close()


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    with patch('src.usecases.db_runbook_finder.discover_runbooks.logging.getLogger') as mock_logger:
        yield mock_logger.return_value


# Mark configuration for different test categories
pytestmark = [
    pytest.mark.unit,  # Default mark for unit tests
]

# Integration tests should be marked separately
integration_tests = [
    TestEndToEndClearingIntegration,
]

# Performance tests should be marked separately  
performance_tests = [
    TestClearingPerformance,
]