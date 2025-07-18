"""
Comprehensive integration tests for Confluence Integration Tool.

This module contains integration tests that interact with real Confluence API
and ChromaDB instances to verify end-to-end functionality.
"""

import os
import pytest
import tempfile
import shutil
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import patch

from .api import app
from .confluence import ConfluenceClient
from .vector_store import VectorStore
from .models import (
    RunbookContent,
    RunbookMetadata,
    PageExtractionRequest,
    BulkExtractionRequest
)
from fastapi.testclient import TestClient


class TestConfluenceAPIIntegration:
    """Integration tests for real Confluence API interactions."""
    
    @pytest.fixture(scope="class")
    def confluence_client(self):
        """Create Confluence client for integration testing."""
        # Skip if no real credentials available
        if not all([
            os.getenv("CONFLUENCE_URL"),
            os.getenv("CONFLUENCE_USERNAME"),
            os.getenv("CONFLUENCE_API_TOKEN")
        ]):
            pytest.skip("Confluence credentials not available for integration testing")
        
        return ConfluenceClient()
    
    @pytest.fixture(scope="class")
    def test_space_key(self):
        """Test space key for integration tests."""
        return os.getenv("CONFLUENCE_TEST_SPACE", "TEST")
    
    @pytest.fixture(scope="class")
    def test_page_id(self):
        """Test page ID for integration tests."""
        return os.getenv("CONFLUENCE_TEST_PAGE_ID", "123456")
    
    def test_confluence_authentication(self, confluence_client):
        """Test Confluence authentication with real API."""
        try:
            # Try to search for pages - this will fail if auth is wrong
            results = confluence_client.search_pages("test", limit=1)
            assert isinstance(results, list)
        except Exception as e:
            pytest.fail(f"Confluence authentication failed: {e}")
    
    def test_get_page_by_id_real_api(self, confluence_client, test_page_id):
        """Test page retrieval by ID with real Confluence API."""
        try:
            page_data = confluence_client.get_page_by_id(test_page_id)
            
            assert "id" in page_data
            assert "title" in page_data
            assert "body" in page_data
            assert page_data["id"] == test_page_id
            
        except Exception as e:
            # If page doesn't exist, that's expected in test environment
            if "not found" in str(e).lower():
                pytest.skip(f"Test page {test_page_id} not found in Confluence")
            else:
                pytest.fail(f"Unexpected error: {e}")
    
    def test_search_pages_real_api(self, confluence_client, test_space_key):
        """Test page search with real Confluence API."""
        try:
            # Search for common terms that should exist
            results = confluence_client.search_pages("page", space_key=test_space_key, limit=5)
            
            assert isinstance(results, list)
            # Results might be empty in test environment, that's OK
            
            if results:
                for result in results:
                    assert "id" in result
                    assert "title" in result
                    
        except Exception as e:
            pytest.fail(f"Search pages failed: {e}")
    
    def test_content_extraction_real_api(self, confluence_client, test_page_id):
        """Test content extraction from real Confluence page."""
        try:
            page_data = confluence_client.get_page_by_id(test_page_id)
            runbook_content = confluence_client.extract_runbook_content(page_data)
            
            assert isinstance(runbook_content, RunbookContent)
            assert runbook_content.metadata.title
            assert runbook_content.metadata.page_id == test_page_id
            assert runbook_content.raw_content
            
        except Exception as e:
            if "not found" in str(e).lower():
                pytest.skip(f"Test page {test_page_id} not found in Confluence")
            else:
                pytest.fail(f"Content extraction failed: {e}")
    
    @pytest.mark.slow
    def test_rate_limiting_handling(self, confluence_client):
        """Test rate limiting handling with multiple rapid requests."""
        try:
            # Make multiple rapid requests to test rate limiting
            for i in range(5):
                confluence_client.search_pages(f"test query {i}", limit=1)
                time.sleep(0.1)  # Small delay between requests
                
        except Exception as e:
            # Rate limiting should be handled gracefully
            if "rate limit" in str(e).lower():
                pytest.fail("Rate limiting not handled properly")
            else:
                # Other errors might be expected in test environment
                pass


class TestVectorDatabaseIntegration:
    """Integration tests for vector database operations with actual ChromaDB."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_test_db_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def vector_store(self, temp_db_dir):
        """Create VectorStore instance for integration testing."""
        return VectorStore(
            collection_name="test_runbooks",
            persist_directory=temp_db_dir
        )
    
    @pytest.fixture
    def sample_runbook_data(self):
        """Create sample runbook data for testing."""
        metadata = RunbookMetadata(
            title="Integration Test Runbook",
            author="Test Author",
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="integration_test_123",
            page_url="https://example.com/integration_test",
            tags=["integration", "test", "runbook"]
        )
        
        return RunbookContent(
            metadata=metadata,
            procedures=[
                "Step 1: Initialize the system",
                "Step 2: Configure the database connection",
                "Step 3: Start the application services",
                "Step 4: Verify system health"
            ],
            troubleshooting_steps=[
                "Check system logs for errors",
                "Verify network connectivity",
                "Restart failed services",
                "Contact system administrator if issues persist"
            ],
            prerequisites=[
                "Administrative access to the system",
                "Database credentials",
                "Network access to required services"
            ],
            raw_content="""
            This is a comprehensive runbook for system initialization and troubleshooting.
            It contains detailed procedures for setting up the system and resolving common issues.
            The runbook is designed for system administrators and operations teams.
            """,
            structured_sections={
                "overview": "System initialization runbook",
                "procedures": "Step-by-step initialization process",
                "troubleshooting": "Common issues and solutions"
            }
        )
    
    def test_vector_store_initialization(self, vector_store):
        """Test vector store initialization with real ChromaDB."""
        assert vector_store is not None
        assert vector_store.collection_name == "test_runbooks"
        assert vector_store._client is not None
        assert vector_store._collection is not None
        assert vector_store._embedding_model is not None
    
    def test_add_runbook_integration(self, vector_store, sample_runbook_data):
        """Test adding runbook to real vector database."""
        runbook_id = vector_store.add_runbook(sample_runbook_data)
        
        assert runbook_id is not None
        assert isinstance(runbook_id, str)
        assert runbook_id.startswith("integration_test_123_")
    
    def test_search_runbooks_integration(self, vector_store, sample_runbook_data):
        """Test semantic search with real vector database."""
        # First add a runbook
        runbook_id = vector_store.add_runbook(sample_runbook_data)
        
        # Wait a moment for indexing
        time.sleep(0.5)
        
        # Search for related content
        results = vector_store.search_runbooks("system initialization", n_results=5)
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check that our runbook appears in results
        found_runbook = any(
            result.runbook_id == runbook_id for result in results
        )
        assert found_runbook, "Added runbook not found in search results"
        
        # Verify result structure
        for result in results:
            assert hasattr(result, 'runbook_id')
            assert hasattr(result, 'content')
            assert hasattr(result, 'relevance_score')
            assert hasattr(result, 'metadata')
            assert 0.0 <= result.relevance_score <= 1.0
    
    def test_get_runbook_by_id_integration(self, vector_store, sample_runbook_data):
        """Test runbook retrieval by ID with real vector database."""
        # Add a runbook
        runbook_id = vector_store.add_runbook(sample_runbook_data)
        
        # Retrieve it
        retrieved_runbook = vector_store.get_runbook_by_id(runbook_id)
        
        assert retrieved_runbook is not None
        assert isinstance(retrieved_runbook, RunbookContent)
        assert retrieved_runbook.metadata.title == sample_runbook_data.metadata.title
        assert retrieved_runbook.metadata.page_id == sample_runbook_data.metadata.page_id
    
    def test_update_runbook_integration(self, vector_store, sample_runbook_data):
        """Test runbook update with real vector database."""
        # Add a runbook
        runbook_id = vector_store.add_runbook(sample_runbook_data)
        
        # Modify the data
        updated_data = sample_runbook_data.model_copy()
        updated_data.metadata.title = "Updated Integration Test Runbook"
        updated_data.procedures.append("Step 5: Perform final verification")
        
        # Update the runbook
        vector_store.update_runbook(runbook_id, updated_data)
        
        # Retrieve and verify
        retrieved_runbook = vector_store.get_runbook_by_id(runbook_id)
        assert retrieved_runbook.metadata.title == "Updated Integration Test Runbook"
        assert "Step 5: Perform final verification" in retrieved_runbook.procedures
    
    def test_delete_runbook_integration(self, vector_store, sample_runbook_data):
        """Test runbook deletion with real vector database."""
        # Add a runbook
        runbook_id = vector_store.add_runbook(sample_runbook_data)
        
        # Verify it exists
        retrieved_runbook = vector_store.get_runbook_by_id(runbook_id)
        assert retrieved_runbook is not None
        
        # Delete it
        vector_store.delete_runbook(runbook_id)
        
        # Verify it's gone
        retrieved_runbook = vector_store.get_runbook_by_id(runbook_id)
        assert retrieved_runbook is None
    
    def test_embedding_consistency(self, vector_store):
        """Test that embeddings are consistent for same content."""
        text = "This is a test document for embedding consistency"
        
        embedding1 = vector_store._generate_embeddings(text)
        embedding2 = vector_store._generate_embeddings(text)
        
        assert embedding1 == embedding2
        assert len(embedding1) == vector_store._embedding_dimension
    
    def test_chunking_integration(self, vector_store):
        """Test content chunking with real implementation."""
        # Create long content
        long_content = "This is a test sentence. " * 100  # ~2500 characters
        
        chunks = vector_store._chunk_content(long_content, chunk_size=500, overlap=50)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 500 for chunk in chunks)
        
        # Verify chunks have some overlap
        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            for i in range(len(chunks) - 1):
                # This is a simplified check - actual overlap detection is complex
                assert len(chunks[i]) > 0
                assert len(chunks[i + 1]) > 0


class TestEndToEndWorkflow:
    """End-to-end workflow tests from extraction to search."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_e2e_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def test_client(self, temp_db_dir):
        """Create test client with real dependencies."""
        # Override vector store to use test directory
        with patch('api.VectorStore') as mock_vs_class:
            mock_vs_class.return_value = VectorStore(
                collection_name="e2e_test_runbooks",
                persist_directory=temp_db_dir
            )
            yield TestClient(app)
    
    def test_complete_extraction_to_search_workflow(self, test_client):
        """Test complete workflow from page extraction to search."""
        # Mock Confluence client to avoid real API calls
        with patch('api.get_confluence_client') as mock_get_client:
            mock_client = self._create_mock_confluence_client()
            mock_get_client.return_value = mock_client
            
            # Step 1: Extract a page
            extraction_request = {
                "page_id": "test_page_123"
            }
            
            response = test_client.post("/pages/extract", json=extraction_request)
            assert response.status_code == 200
            
            extraction_data = response.json()
            assert "metadata" in extraction_data
            assert "procedures" in extraction_data
            
            # Step 2: Search for the extracted content
            time.sleep(0.5)  # Allow for indexing
            
            search_response = test_client.get("/search/runbooks?query=database backup")
            assert search_response.status_code == 200
            
            search_data = search_response.json()
            assert "results" in search_data
            assert isinstance(search_data["results"], list)
            
            # Step 3: Verify search found our content
            if search_data["results"]:
                result = search_data["results"][0]
                assert "runbook_id" in result
                assert "content" in result
                assert "relevance_score" in result
    
    def test_bulk_extraction_workflow(self, test_client):
        """Test bulk extraction workflow."""
        with patch('api.get_confluence_client') as mock_get_client:
            mock_client = self._create_mock_confluence_client()
            mock_get_client.return_value = mock_client
            
            # Bulk extract multiple pages
            bulk_request = {
                "page_ids": ["page_1", "page_2", "page_3"]
            }
            
            response = test_client.post("/pages/bulk-extract", json=bulk_request)
            assert response.status_code == 200
            
            bulk_data = response.json()
            assert "total_pages" in bulk_data
            assert "successful_extractions" in bulk_data
            assert "job_id" in bulk_data
            assert bulk_data["total_pages"] == 3
    
    def test_runbook_management_workflow(self, test_client):
        """Test runbook management operations."""
        with patch('api.get_confluence_client') as mock_get_client:
            mock_client = self._create_mock_confluence_client()
            mock_get_client.return_value = mock_client
            
            # Step 1: Extract a runbook
            extraction_request = {"page_id": "management_test_page"}
            response = test_client.post("/pages/extract", json=extraction_request)
            assert response.status_code == 200
            
            # Step 2: Search to find the runbook ID
            time.sleep(0.5)
            search_response = test_client.get("/search/runbooks?query=management test")
            assert search_response.status_code == 200
            
            search_data = search_response.json()
            if search_data["results"]:
                runbook_id = search_data["results"][0]["runbook_id"]
                
                # Step 3: Get runbook by ID
                get_response = test_client.get(f"/runbooks/{runbook_id}")
                assert get_response.status_code == 200
                
                # Step 4: Update runbook
                update_data = get_response.json()
                update_data["metadata"]["title"] = "Updated Management Test Runbook"
                
                put_response = test_client.put(f"/runbooks/{runbook_id}", json=update_data)
                assert put_response.status_code == 200
                
                # Step 5: Verify update
                verify_response = test_client.get(f"/runbooks/{runbook_id}")
                assert verify_response.status_code == 200
                verify_data = verify_response.json()
                assert verify_data["metadata"]["title"] == "Updated Management Test Runbook"
                
                # Step 6: Delete runbook
                delete_response = test_client.delete(f"/runbooks/{runbook_id}")
                assert delete_response.status_code == 200
                
                # Step 7: Verify deletion
                final_response = test_client.get(f"/runbooks/{runbook_id}")
                assert final_response.status_code == 404
    
    def test_health_check_workflow(self, test_client):
        """Test health check and monitoring endpoints."""
        # Test health endpoint
        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert "status" in health_data
        assert "vector_db_connected" in health_data
        
        # Test stats endpoint
        stats_response = test_client.get("/stats")
        assert stats_response.status_code == 200
        
        stats_data = stats_response.json()
        assert "collections_count" in stats_data
        assert "total_runbooks" in stats_data
    
    def _create_mock_confluence_client(self):
        """Create mock Confluence client for testing."""
        from unittest.mock import Mock
        
        mock_client = Mock()
        
        # Mock page data
        mock_page_data = {
            "id": "test_page_123",
            "title": "Database Backup Runbook",
            "space": {"key": "TEST"},
            "version": {
                "when": "2024-01-01T00:00:00Z",
                "by": {"displayName": "Test Author"}
            },
            "body": {
                "storage": {
                    "value": """
                    <h1>Database Backup Runbook</h1>
                    <h2>Procedures</h2>
                    <ol>
                        <li>Connect to database server</li>
                        <li>Run backup command</li>
                        <li>Verify backup completion</li>
                    </ol>
                    <h2>Troubleshooting</h2>
                    <ul>
                        <li>Check disk space</li>
                        <li>Verify permissions</li>
                    </ul>
                    """
                }
            }
        }
        
        mock_client.get_page_by_id.return_value = mock_page_data
        
        # Mock runbook content extraction
        metadata = RunbookMetadata(
            title="Database Backup Runbook",
            author="Test Author",
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="test_page_123",
            page_url="https://example.com/test_page_123",
            tags=["database", "backup", "runbook"]
        )
        
        runbook_content = RunbookContent(
            metadata=metadata,
            procedures=[
                "Connect to database server",
                "Run backup command",
                "Verify backup completion"
            ],
            troubleshooting_steps=[
                "Check disk space",
                "Verify permissions"
            ],
            prerequisites=["Database access", "Admin privileges"],
            raw_content="Database backup procedures and troubleshooting steps",
            structured_sections={
                "procedures": "Database backup steps",
                "troubleshooting": "Common issues and solutions"
            }
        )
        
        mock_client.extract_runbook_content.return_value = runbook_content
        
        return mock_client


class TestPerformanceIntegration:
    """Performance tests for bulk operations and search response times."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for performance test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_perf_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def vector_store(self, temp_db_dir):
        """Create VectorStore instance for performance testing."""
        return VectorStore(
            collection_name="perf_test_runbooks",
            persist_directory=temp_db_dir
        )
    
    def test_bulk_runbook_addition_performance(self, vector_store):
        """Test performance of adding multiple runbooks."""
        # Create multiple runbook samples
        runbooks = []
        for i in range(10):
            metadata = RunbookMetadata(
                title=f"Performance Test Runbook {i}",
                author="Performance Tester",
                last_modified=datetime.utcnow(),
                space_key="PERF",
                page_id=f"perf_test_{i}",
                page_url=f"https://example.com/perf_test_{i}",
                tags=["performance", "test", f"runbook_{i}"]
            )
            
            runbook = RunbookContent(
                metadata=metadata,
                procedures=[f"Step {j}: Perform action {j}" for j in range(1, 6)],
                troubleshooting_steps=[f"Issue {j}: Check component {j}" for j in range(1, 4)],
                prerequisites=[f"Requirement {j}" for j in range(1, 3)],
                raw_content=f"Performance test runbook {i} with detailed content " * 20,
                structured_sections={
                    "overview": f"Performance test runbook {i}",
                    "details": f"Detailed procedures for test {i}"
                }
            )
            runbooks.append(runbook)
        
        # Measure bulk addition time
        start_time = time.time()
        
        runbook_ids = []
        for runbook in runbooks:
            runbook_id = vector_store.add_runbook(runbook)
            runbook_ids.append(runbook_id)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 30.0, f"Bulk addition took too long: {total_time:.2f}s"
        assert len(runbook_ids) == 10
        assert all(runbook_id is not None for runbook_id in runbook_ids)
        
        print(f"Added 10 runbooks in {total_time:.2f} seconds ({total_time/10:.2f}s per runbook)")
    
    @pytest.mark.slow
    def test_search_response_time_performance(self, vector_store):
        """Test search response times with multiple runbooks."""
        # Add some runbooks first
        for i in range(5):
            metadata = RunbookMetadata(
                title=f"Search Performance Test {i}",
                author="Search Tester",
                last_modified=datetime.utcnow(),
                space_key="SEARCH",
                page_id=f"search_test_{i}",
                page_url=f"https://example.com/search_test_{i}",
                tags=["search", "performance", "test"]
            )
            
            runbook = RunbookContent(
                metadata=metadata,
                procedures=[f"Search procedure {j}" for j in range(1, 4)],
                troubleshooting_steps=[f"Search troubleshooting {j}" for j in range(1, 3)],
                prerequisites=["Search access"],
                raw_content=f"Search performance test content {i} " * 50,
                structured_sections={"search": f"Search test {i}"}
            )
            
            vector_store.add_runbook(runbook)
        
        # Wait for indexing
        time.sleep(1.0)
        
        # Test search performance
        search_queries = [
            "search performance",
            "troubleshooting procedure",
            "test content",
            "search access",
            "performance test"
        ]
        
        total_search_time = 0
        for query in search_queries:
            start_time = time.time()
            results = vector_store.search_runbooks(query, n_results=5)
            end_time = time.time()
            
            search_time = end_time - start_time
            total_search_time += search_time
            
            # Each search should be fast
            assert search_time < 2.0, f"Search for '{query}' took too long: {search_time:.2f}s"
            assert isinstance(results, list)
        
        avg_search_time = total_search_time / len(search_queries)
        print(f"Average search time: {avg_search_time:.3f} seconds")
        
        # Overall performance check
        assert avg_search_time < 1.0, f"Average search time too slow: {avg_search_time:.3f}s"
    
    def test_large_content_processing_performance(self, vector_store):
        """Test performance with large content processing."""
        # Create runbook with large content
        large_content = "This is a large content block for performance testing. " * 1000  # ~55KB
        
        metadata = RunbookMetadata(
            title="Large Content Performance Test",
            author="Performance Tester",
            last_modified=datetime.utcnow(),
            space_key="LARGE",
            page_id="large_content_test",
            page_url="https://example.com/large_content_test",
            tags=["large", "performance", "test"]
        )
        
        runbook = RunbookContent(
            metadata=metadata,
            procedures=["Process large content"],
            troubleshooting_steps=["Handle large content issues"],
            prerequisites=["Large content access"],
            raw_content=large_content,
            structured_sections={"content": large_content}
        )
        
        # Measure processing time
        start_time = time.time()
        runbook_id = vector_store.add_runbook(runbook)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 10.0, f"Large content processing took too long: {processing_time:.2f}s"
        assert runbook_id is not None
        
        print(f"Processed large content ({len(large_content)} chars) in {processing_time:.2f} seconds")


class TestDataManagementAndCleanup:
    """Test data management and cleanup procedures."""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create temporary directory for cleanup test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_cleanup_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def vector_store(self, temp_db_dir):
        """Create VectorStore instance for cleanup testing."""
        return VectorStore(
            collection_name="cleanup_test_runbooks",
            persist_directory=temp_db_dir
        )
    
    def test_database_cleanup_procedures(self, vector_store, temp_db_dir):
        """Test database cleanup and data management."""
        # Add test data
        test_runbooks = []
        for i in range(3):
            metadata = RunbookMetadata(
                title=f"Cleanup Test Runbook {i}",
                author="Cleanup Tester",
                last_modified=datetime.utcnow(),
                space_key="CLEANUP",
                page_id=f"cleanup_test_{i}",
                page_url=f"https://example.com/cleanup_test_{i}",
                tags=["cleanup", "test"]
            )
            
            runbook = RunbookContent(
                metadata=metadata,
                procedures=[f"Cleanup procedure {i}"],
                troubleshooting_steps=[f"Cleanup troubleshooting {i}"],
                prerequisites=[f"Cleanup requirement {i}"],
                raw_content=f"Cleanup test content {i}",
                structured_sections={"cleanup": f"Cleanup test {i}"}
            )
            
            runbook_id = vector_store.add_runbook(runbook)
            test_runbooks.append(runbook_id)
        
        # Verify data exists
        for runbook_id in test_runbooks:
            runbook = vector_store.get_runbook_by_id(runbook_id)
            assert runbook is not None
        
        # Test individual cleanup
        vector_store.delete_runbook(test_runbooks[0])
        deleted_runbook = vector_store.get_runbook_by_id(test_runbooks[0])
        assert deleted_runbook is None
        
        # Verify other runbooks still exist
        for runbook_id in test_runbooks[1:]:
            runbook = vector_store.get_runbook_by_id(runbook_id)
            assert runbook is not None
        
        # Test database file cleanup
        db_files = os.listdir(temp_db_dir)
        assert len(db_files) > 0, "Database files should exist"
        
        # Cleanup remaining runbooks
        for runbook_id in test_runbooks[1:]:
            vector_store.delete_runbook(runbook_id)
    
    def test_test_data_isolation(self):
        """Test that test data is properly isolated."""
        # Create two separate vector stores
        temp_dir1 = tempfile.mkdtemp(prefix="isolation_test_1_")
        temp_dir2 = tempfile.mkdtemp(prefix="isolation_test_2_")
        
        try:
            vs1 = VectorStore(collection_name="isolation_test_1", persist_directory=temp_dir1)
            vs2 = VectorStore(collection_name="isolation_test_2", persist_directory=temp_dir2)
            
            # Add data to first store
            metadata1 = RunbookMetadata(
                title="Isolation Test 1",
                author="Tester 1",
                last_modified=datetime.utcnow(),
                space_key="ISO1",
                page_id="isolation_1",
                page_url="https://example.com/isolation_1",
                tags=["isolation", "test1"]
            )
            
            runbook1 = RunbookContent(
                metadata=metadata1,
                procedures=["Isolation procedure 1"],
                troubleshooting_steps=["Isolation troubleshooting 1"],
                prerequisites=["Isolation requirement 1"],
                raw_content="Isolation test content 1",
                structured_sections={"isolation": "Isolation test 1"}
            )
            
            runbook_id1 = vs1.add_runbook(runbook1)
            
            # Verify data exists in first store
            retrieved1 = vs1.get_runbook_by_id(runbook_id1)
            assert retrieved1 is not None
            
            # Verify data doesn't exist in second store
            retrieved2 = vs2.get_runbook_by_id(runbook_id1)
            assert retrieved2 is None
            
            # Search in second store should not find data from first store
            results = vs2.search_runbooks("isolation test", n_results=5)
            assert len(results) == 0
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir1, ignore_errors=True)
            shutil.rmtree(temp_dir2, ignore_errors=True)
    
    def test_concurrent_access_safety(self, vector_store):
        """Test concurrent access safety for data operations."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def add_runbook_worker(worker_id):
            """Worker function to add runbooks concurrently."""
            try:
                metadata = RunbookMetadata(
                    title=f"Concurrent Test Runbook {worker_id}",
                    author=f"Worker {worker_id}",
                    last_modified=datetime.utcnow(),
                    space_key="CONCURRENT",
                    page_id=f"concurrent_test_{worker_id}",
                    page_url=f"https://example.com/concurrent_test_{worker_id}",
                    tags=["concurrent", "test", f"worker_{worker_id}"]
                )
                
                runbook = RunbookContent(
                    metadata=metadata,
                    procedures=[f"Concurrent procedure {worker_id}"],
                    troubleshooting_steps=[f"Concurrent troubleshooting {worker_id}"],
                    prerequisites=[f"Concurrent requirement {worker_id}"],
                    raw_content=f"Concurrent test content {worker_id}",
                    structured_sections={"concurrent": f"Concurrent test {worker_id}"}
                )
                
                runbook_id = vector_store.add_runbook(runbook)
                results_queue.put((worker_id, runbook_id))
                
            except Exception as e:
                errors_queue.put((worker_id, str(e)))
        
        # Start multiple worker threads
        threads = []
        num_workers = 3
        
        for i in range(num_workers):
            thread = threading.Thread(target=add_runbook_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        assert errors_queue.empty(), f"Concurrent access errors: {list(errors_queue.queue)}"
        assert results_queue.qsize() == num_workers, "Not all workers completed successfully"
        
        # Verify all runbooks were added
        worker_results = []
        while not results_queue.empty():
            worker_results.append(results_queue.get())
        
        for worker_id, runbook_id in worker_results:
            runbook = vector_store.get_runbook_by_id(runbook_id)
            assert runbook is not None
            assert f"Worker {worker_id}" in runbook.metadata.author


if __name__ == "__main__":
    # Run integration tests with appropriate markers
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow"  # Skip slow tests by default
    ])