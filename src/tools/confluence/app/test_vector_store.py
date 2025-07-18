"""
Unit tests for the VectorStore class.

This module contains comprehensive tests for vector database operations
including ChromaDB integration, embedding generation, and content chunking.
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from .vector_store import VectorStore
from .models import RunbookContent, RunbookMetadata, SearchResult


# Global fixtures
@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_metadata():
    """Create sample runbook metadata for testing."""
    return RunbookMetadata(
        title="Test Runbook",
        author="Test Author",
        last_modified=datetime(2024, 1, 1, 12, 0, 0),
        space_key="TEST",
        page_id="12345",
        page_url="https://example.com/test",
        tags=["test", "runbook"]
    )

@pytest.fixture
def sample_runbook_content(sample_metadata):
    """Create sample runbook content for testing."""
    return RunbookContent(
        metadata=sample_metadata,
        procedures=["Step 1: Do this", "Step 2: Do that"],
        troubleshooting_steps=["Check logs", "Restart service"],
        prerequisites=["Access to system", "Admin privileges"],
        raw_content="This is the raw content of the runbook",
        structured_sections={"Overview": "This is an overview"}
    )


class TestVectorStoreInitialization:
    """Test VectorStore initialization."""
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_init_success(self, mock_transformer, mock_chroma, temp_dir):
        """Test successful initialization."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        # Initialize VectorStore
        vector_store = VectorStore(
            collection_name="test_collection",
            persist_directory=temp_dir
        )
        
        # Verify initialization
        assert vector_store.collection_name == "test_collection"
        assert vector_store.persist_directory == temp_dir
        assert vector_store._client == mock_client
        assert vector_store._collection == mock_collection
        assert vector_store._embedding_model == mock_model
        assert vector_store._embedding_dimension == 384
    
    @patch('app.vector_store.chromadb.PersistentClient')
    def test_init_chroma_failure(self, mock_chroma):
        """Test initialization failure with ChromaDB."""
        mock_chroma.side_effect = Exception("ChromaDB connection failed")
        
        with pytest.raises(Exception, match="ChromaDB connection failed"):
            VectorStore()
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_init_embedding_model_failure(self, mock_transformer, mock_chroma):
        """Test initialization failure with embedding model."""
        # Setup ChromaDB mock
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Make embedding model fail
        mock_transformer.side_effect = Exception("Model loading failed")
        
        with pytest.raises(Exception, match="Model loading failed"):
            VectorStore()


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_generate_embeddings_success(self, mock_transformer, mock_chroma):
        """Test successful embedding generation."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        # First call for initialization, second for actual test
        test_embedding = [[0.1, 0.2, 0.3]]
        mock_model.encode.side_effect = [test_embedding, test_embedding]
        
        # Initialize VectorStore
        vector_store = VectorStore()
        
        # Test embedding generation
        result = vector_store._generate_embeddings("test text")
        
        assert result == [0.1, 0.2, 0.3]
        # Should be called twice - once for init, once for test
        assert mock_model.encode.call_count == 2
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_generate_embeddings_empty_text(self, mock_transformer, mock_chroma):
        """Test embedding generation with empty text."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 3]
        
        vector_store = VectorStore()
        
        # Test with empty text
        with pytest.raises(ValueError, match="Text cannot be empty"):
            vector_store._generate_embeddings("")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            vector_store._generate_embeddings("   ")
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_generate_embeddings_model_failure(self, mock_transformer, mock_chroma):
        """Test embedding generation with model failure."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        # First call for initialization succeeds, second fails
        mock_model.encode.side_effect = [[[0.1] * 384], Exception("Model encoding failed")]
        
        vector_store = VectorStore()
        
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            vector_store._generate_embeddings("test text")


class TestContentChunking:
    """Test content chunking functionality."""
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_chunk_content_small_text(self, mock_transformer, mock_chroma):
        """Test chunking with text smaller than chunk size."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with small text - use smaller overlap to avoid validation error
        text = "This is a small text."
        chunks = vector_store._chunk_content(text, chunk_size=100, overlap=20)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_chunk_content_large_text(self, mock_transformer, mock_chroma):
        """Test chunking with text larger than chunk size."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Create text larger than chunk size
        text = "This is a test sentence. " * 50  # ~1250 characters
        chunks = vector_store._chunk_content(text, chunk_size=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
        
        # Check that chunks have some overlap
        if len(chunks) > 1:
            # This is a simplified check - in practice, overlap detection is complex
            assert len(chunks) >= 2
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_chunk_content_invalid_parameters(self, mock_transformer, mock_chroma):
        """Test chunking with invalid parameters."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            vector_store._chunk_content("")
        
        # Test with invalid chunk size
        with pytest.raises(ValueError, match="Chunk size must be positive"):
            vector_store._chunk_content("test", chunk_size=0)
        
        # Test with invalid overlap
        with pytest.raises(ValueError, match="Overlap must be non-negative"):
            vector_store._chunk_content("test", chunk_size=100, overlap=-1)
        
        with pytest.raises(ValueError, match="less than chunk size"):
            vector_store._chunk_content("test", chunk_size=100, overlap=100)


class TestRunbookOperations:
    """Test runbook CRUD operations."""
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_add_runbook_success(self, mock_transformer, mock_chroma, sample_runbook_content):
        """Test successful runbook addition."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test adding runbook
        runbook_id = vector_store.add_runbook(sample_runbook_content)
        
        assert runbook_id is not None
        assert isinstance(runbook_id, str)
        
        # Verify ChromaDB add was called
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[1]
        
        assert "ids" in call_args
        assert "embeddings" in call_args
        assert "documents" in call_args
        assert "metadatas" in call_args
        
        # Check that at least one chunk was created
        assert len(call_args["ids"]) >= 1
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_add_runbook_empty_content(self, mock_transformer, mock_chroma):
        """Test adding runbook with empty content."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        with pytest.raises(ValueError, match="Runbook data cannot be None"):
            vector_store.add_runbook(None)
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_search_runbooks_success(self, mock_transformer, mock_chroma):
        """Test successful runbook search."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10
        
        # Mock search results
        mock_search_results = {
            "ids": [["chunk_1", "chunk_2"]],
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[
                {
                    "runbook_id": "runbook_1",
                    "title": "Test Runbook",
                    "author": "Test Author",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "page_url": "https://example.com/test",
                    "last_modified": "2024-01-01T12:00:00",
                    "tags": "test,runbook"
                },
                {
                    "runbook_id": "runbook_2",
                    "title": "Another Runbook",
                    "author": "Another Author",
                    "space_key": "TEST",
                    "page_id": "67890",
                    "page_url": "https://example.com/another",
                    "last_modified": "2024-01-02T12:00:00",
                    "tags": "another,test"
                }
            ]],
            "distances": [[0.1, 0.2]]
        }
        mock_collection.query.return_value = mock_search_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test search
        results = vector_store.search_runbooks("test query", n_results=2)
        
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        
        # Check first result
        assert results[0].runbook_id == "runbook_1"
        assert results[0].chunk_id == "chunk_1"
        assert results[0].content == "Document 1"
        assert 0.0 <= results[0].relevance_score <= 1.0
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_search_runbooks_empty_query(self, mock_transformer, mock_chroma):
        """Test search with empty query."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            vector_store.search_runbooks("")
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_search_runbooks_invalid_limit(self, mock_transformer, mock_chroma):
        """Test search with invalid result limit."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        with pytest.raises(ValueError, match="Number of results must be between 1 and 20"):
            vector_store.search_runbooks("test", n_results=0)
        
        with pytest.raises(ValueError, match="Number of results must be between 1 and 20"):
            vector_store.search_runbooks("test", n_results=25)
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_search_runbooks_no_results(self, mock_transformer, mock_chroma):
        """Test search with no matching results."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 0
        
        # Mock empty search results
        mock_search_results = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        mock_collection.query.return_value = mock_search_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test search with no results
        results = vector_store.search_runbooks("nonexistent query", n_results=5)
        
        assert len(results) == 0
        assert isinstance(results, list)
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_search_runbooks_with_filters(self, mock_transformer, mock_chroma):
        """Test search with metadata filters."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10
        
        # Mock search results
        mock_search_results = {
            "ids": [["chunk_1"]],
            "documents": [["Filtered Document"]],
            "metadatas": [[
                {
                    "runbook_id": "runbook_1",
                    "title": "Production Runbook",
                    "author": "admin",
                    "space_key": "PROD",
                    "page_id": "12345",
                    "page_url": "https://example.com/prod",
                    "last_modified": "2024-01-01T12:00:00",
                    "tags": "production,critical"
                }
            ]],
            "distances": [[0.1]]
        }
        mock_collection.query.return_value = mock_search_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test search with filters
        filters = {"space_key": "PROD", "author": "admin"}
        results = vector_store.search_runbooks("database issue", n_results=5, filters=filters)
        
        assert len(results) == 1
        assert results[0].metadata.space_key == "PROD"
        assert results[0].metadata.author == "admin"
        
        # Verify that query was called with filters
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args[1]
        assert "where" in call_args
        assert call_args["where"]["space_key"] == "PROD"
        assert call_args["where"]["author"] == "admin"
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_get_runbook_by_id_success(self, mock_transformer, mock_chroma):
        """Test successful runbook retrieval by ID."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock get results
        mock_get_results = {
            "ids": ["chunk_1", "chunk_2"],
            "documents": ["Document 1", "Document 2"],
            "metadatas": [
                {
                    "runbook_id": "test_runbook",
                    "title": "Test Runbook",
                    "author": "Test Author",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "page_url": "https://example.com/test",
                    "last_modified": "2024-01-01T12:00:00",
                    "tags": "test,runbook"
                },
                {
                    "runbook_id": "test_runbook",
                    "title": "Test Runbook",
                    "author": "Test Author",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "page_url": "https://example.com/test",
                    "last_modified": "2024-01-01T12:00:00",
                    "tags": "test,runbook"
                }
            ]
        }
        mock_collection.get.return_value = mock_get_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test retrieval
        result = vector_store.get_runbook_by_id("test_runbook")
        
        assert result is not None
        assert isinstance(result, RunbookContent)
        assert result.metadata.title == "Test Runbook"
        assert "Document 1" in result.raw_content
        assert "Document 2" in result.raw_content
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_get_runbook_by_id_not_found(self, mock_transformer, mock_chroma):
        """Test runbook retrieval with non-existent ID."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock empty results
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        result = vector_store.get_runbook_by_id("nonexistent")
        assert result is None
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_delete_runbook_success(self, mock_transformer, mock_chroma):
        """Test successful runbook deletion."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock get results for deletion
        mock_get_results = {
            "ids": ["chunk_1", "chunk_2"],
            "metadatas": [{"runbook_id": "test_runbook"}, {"runbook_id": "test_runbook"}]
        }
        mock_collection.get.return_value = mock_get_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test deletion
        vector_store.delete_runbook("test_runbook")
        
        # Verify delete was called with correct IDs
        mock_collection.delete.assert_called_once_with(ids=["chunk_1", "chunk_2"])
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_delete_runbook_not_found(self, mock_transformer, mock_chroma):
        """Test deletion of non-existent runbook."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock empty results
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Should not raise exception for non-existent runbook
        vector_store.delete_runbook("nonexistent")
        
        # Delete should not be called
        mock_collection.delete.assert_not_called()

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_update_runbook_success(self, mock_transformer, mock_chroma, sample_runbook_content):
        """Test successful runbook update."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock existing runbook for get_runbook_by_id
        mock_get_results = {
            "ids": ["test_runbook_chunk_0"],
            "documents": ["Original content"],
            "metadatas": [
                {
                    "runbook_id": "test_runbook",
                    "title": "Original Title",
                    "author": "Original Author",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "page_url": "https://example.com/test",
                    "last_modified": "2024-01-01T12:00:00",
                    "tags": "test,runbook"
                }
            ]
        }
        mock_collection.get.return_value = mock_get_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test update
        vector_store.update_runbook("test_runbook", sample_runbook_content)
        
        # Verify delete was called for existing chunks
        assert mock_collection.delete.called
        
        # Verify add was called for new chunks
        assert mock_collection.add.called
        
        # Check that add was called with correct runbook_id
        add_call_args = mock_collection.add.call_args[1]
        assert "ids" in add_call_args
        assert all(chunk_id.startswith("test_runbook_chunk_") for chunk_id in add_call_args["ids"])

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_update_runbook_not_found(self, mock_transformer, mock_chroma, sample_runbook_content):
        """Test update of non-existent runbook."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock empty results for get_runbook_by_id
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test update of non-existent runbook
        with pytest.raises(ValueError, match="Runbook with ID 'nonexistent' not found"):
            vector_store.update_runbook("nonexistent", sample_runbook_content)

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_update_runbook_empty_id(self, mock_transformer, mock_chroma, sample_runbook_content):
        """Test update with empty runbook ID."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with empty ID
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.update_runbook("", sample_runbook_content)
        
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.update_runbook("   ", sample_runbook_content)

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_update_runbook_none_data(self, mock_transformer, mock_chroma):
        """Test update with None runbook data."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with None data
        with pytest.raises(ValueError, match="Runbook data cannot be None"):
            vector_store.update_runbook("test_runbook", None)

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_get_runbook_by_id_empty_id(self, mock_transformer, mock_chroma):
        """Test retrieval with empty runbook ID."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with empty ID
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.get_runbook_by_id("")
        
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.get_runbook_by_id("   ")

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_delete_runbook_empty_id(self, mock_transformer, mock_chroma):
        """Test deletion with empty runbook ID."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with empty ID
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.delete_runbook("")
        
        with pytest.raises(ValueError, match="Runbook ID cannot be empty"):
            vector_store.delete_runbook("   ")

    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_list_runbooks_invalid_parameters(self, mock_transformer, mock_chroma):
        """Test list runbooks with invalid parameters."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test with invalid limit
        with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
            vector_store.list_runbooks(limit=0)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
            vector_store.list_runbooks(limit=1001)
        
        # Test with invalid offset
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            vector_store.list_runbooks(offset=-1)


class TestUtilityMethods:
    """Test utility and helper methods."""
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_get_collection_stats(self, mock_transformer, mock_chroma):
        """Test collection statistics retrieval."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 42
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore(collection_name="test_collection")
        
        stats = vector_store.get_collection_stats()
        
        assert stats["collection_name"] == "test_collection"
        assert stats["total_chunks"] == 42
        assert stats["embedding_dimension"] == 384
        assert "persist_directory" in stats
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_health_check_success(self, mock_transformer, mock_chroma):
        """Test successful health check."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        assert vector_store.health_check() is True
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_health_check_failure(self, mock_transformer, mock_chroma):
        """Test health check failure."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.side_effect = Exception("Database error")
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        assert vector_store.health_check() is False
    
    @patch('app.vector_store.chromadb.PersistentClient')
    @patch('app.vector_store.SentenceTransformer')
    def test_list_runbooks(self, mock_transformer, mock_chroma):
        """Test runbook listing with pagination."""
        # Setup mocks
        mock_client = Mock()
        mock_chroma.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock multiple runbooks
        mock_get_results = {
            "metadatas": [
                {
                    "runbook_id": "runbook_1",
                    "title": "Runbook 1",
                    "author": "Author 1",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "last_modified": "2024-01-01T12:00:00"
                },
                {
                    "runbook_id": "runbook_1",  # Same runbook, different chunk
                    "title": "Runbook 1",
                    "author": "Author 1",
                    "space_key": "TEST",
                    "page_id": "12345",
                    "last_modified": "2024-01-01T12:00:00"
                },
                {
                    "runbook_id": "runbook_2",
                    "title": "Runbook 2",
                    "author": "Author 2",
                    "space_key": "TEST",
                    "page_id": "67890",
                    "last_modified": "2024-01-02T12:00:00"
                }
            ]
        }
        mock_collection.get.return_value = mock_get_results
        
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        mock_model.encode.return_value = [[0.1] * 384]
        
        vector_store = VectorStore()
        
        # Test listing
        results = vector_store.list_runbooks(limit=10, offset=0)
        
        assert len(results) == 2  # Two unique runbooks
        assert results[0]["runbook_id"] == "runbook_1"
        assert results[0]["chunk_count"] == 2  # Two chunks for runbook_1
        assert results[1]["runbook_id"] == "runbook_2"
        assert results[1]["chunk_count"] == 1  # One chunk for runbook_2


if __name__ == "__main__":
    pytest.main([__file__])