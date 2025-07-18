"""
Integration tests for Confluence Integration Tool API endpoints.

Tests the FastAPI endpoints for page extraction functionality,
including both single page and bulk extraction operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

from .api import app
from .models import (
    PageExtractionRequest,
    BulkExtractionRequest,
    RunbookContent,
    RunbookMetadata,
    BulkExtractionResponse
)
from .confluence import ConfluenceAPIError


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_confluence_client():
    """Mock Confluence client for testing."""
    mock_client = Mock()
    
    # Mock page data
    mock_page_data = {
        "id": "123456",
        "title": "Test Runbook",
        "space": {"key": "TEST"},
        "version": {"when": "2024-01-01T00:00:00Z", "by": {"displayName": "Test User"}},
        "body": {"storage": {"value": "<h1>Test Runbook</h1><p>Test content</p>"}}
    }
    
    mock_client.get_page_by_id.return_value = mock_page_data
    mock_client.get_page_by_title.return_value = mock_page_data
    
    # Mock runbook content
    mock_metadata = RunbookMetadata(
        title="Test Runbook",
        author="Test User",
        last_modified=datetime.utcnow(),
        space_key="TEST",
        page_id="123456",
        page_url="http://test.com/pages/123456",
        tags=[]
    )
    
    mock_runbook_content = RunbookContent(
        metadata=mock_metadata,
        procedures=["Step 1: Do something", "Step 2: Do something else"],
        troubleshooting_steps=["Check logs", "Restart service"],
        prerequisites=["Access to system"],
        raw_content="Test runbook content",
        structured_sections={"procedures": "Step 1: Do something\nStep 2: Do something else"}
    )
    
    mock_client.extract_runbook_content.return_value = mock_runbook_content
    
    return mock_client


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing."""
    mock_store = Mock()
    mock_store.add_runbook.return_value = "test-runbook-id-123"
    return mock_store


class TestPageExtractionEndpoints:
    """Test cases for page extraction endpoints."""
    
    def test_extract_page_by_id_success(self, client, mock_confluence_client, mock_vector_store):
        """Test successful page extraction by ID."""
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=mock_confluence_client), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=mock_vector_store):
            
            request_data = {
                "page_id": "123456"
            }
            
            response = client.post("/pages/extract", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["metadata"]["title"] == "Test Runbook"
            assert data["metadata"]["page_id"] == "123456"
            assert len(data["procedures"]) == 2
            assert len(data["troubleshooting_steps"]) == 2
            
            # Verify client methods were called
            mock_confluence_client.get_page_by_id.assert_called_once_with("123456")
            mock_confluence_client.extract_runbook_content.assert_called_once()
            mock_vector_store.add_runbook.assert_called_once()
    
    def test_extract_page_by_title_success(self, client, mock_confluence_client, mock_vector_store):
        """Test successful page extraction by space key and title."""
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=mock_confluence_client), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=mock_vector_store):
            
            request_data = {
                "space_key": "TEST",
                "title": "Test Runbook"
            }
            
            response = client.post("/pages/extract", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["metadata"]["title"] == "Test Runbook"
            assert data["metadata"]["space_key"] == "TEST"
            
            # Verify client methods were called
            mock_confluence_client.get_page_by_title.assert_called_once_with("TEST", "Test Runbook")
            mock_confluence_client.extract_runbook_content.assert_called_once()
            mock_vector_store.add_runbook.assert_called_once()
    
    def test_extract_page_missing_parameters(self, client):
        """Test page extraction with missing required parameters."""
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=Mock()), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=Mock()):
            
            request_data = {}  # No page_id or space_key/title
            
            response = client.post("/pages/extract", json=request_data)
            
            assert response.status_code == 422
            data = response.json()
            assert "Either page_id or both space_key and title must be provided" in str(data)
    
    def test_extract_page_not_found(self, client):
        """Test page extraction when page is not found."""
        mock_confluence_client = Mock()
        mock_confluence_client.get_page_by_id.side_effect = ConfluenceAPIError("Page not found", status_code=404)
        
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=mock_confluence_client), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=Mock()):
            
            request_data = {
                "page_id": "nonexistent"
            }
            
            response = client.post("/pages/extract", json=request_data)
            
            assert response.status_code == 404
            data = response.json()
            assert "Page not found" in data["detail"]
    
    def test_extract_page_authentication_error(self, client):
        """Test page extraction with authentication failure."""
        mock_confluence_client = Mock()
        mock_confluence_client.get_page_by_id.side_effect = ConfluenceAPIError("Authentication failed", status_code=401)
        
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=mock_confluence_client), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=Mock()):
            
            request_data = {
                "page_id": "123456"
            }
            
            response = client.post("/pages/extract", json=request_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "Authentication failed" in data["detail"]


class TestBulkExtractionEndpoints:
    """Test cases for bulk extraction endpoints."""
    
    def test_bulk_extract_success(self, client):
        """Test successful bulk page extraction."""
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=Mock()), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=Mock()), \
             patch('manager.src.tools.confluence.app.api.extract_single_page') as mock_extract:
            
            # Mock successful extraction results
            mock_extract.side_effect = [
                {
                    "page_id": "123456",
                    "runbook_id": "runbook-1",
                    "title": "Test Runbook 1",
                    "success": True,
                    "error": None
                },
                {
                    "page_id": "789012",
                    "runbook_id": "runbook-2",
                    "title": "Test Runbook 2",
                    "success": True,
                    "error": None
                }
            ]
            
            request_data = {
                "page_ids": ["123456", "789012"]
            }
            
            response = client.post("/pages/bulk-extract", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_pages"] == 2
            assert data["successful_extractions"] == 2
            assert data["failed_extractions"] == 0
            assert len(data["errors"]) == 0
            assert "job_id" in data
            assert data["processing_time"] >= 0
    
    def test_bulk_extract_partial_failure(self, client):
        """Test bulk extraction with some failures."""
        with patch('manager.src.tools.confluence.app.api.get_confluence_client', return_value=Mock()), \
             patch('manager.src.tools.confluence.app.api.get_vector_store', return_value=Mock()), \
             patch('manager.src.tools.confluence.app.api.extract_single_page') as mock_extract:
            
            # Mock mixed results - one success, one failure
            mock_extract.side_effect = [
                {
                    "page_id": "123456",
                    "runbook_id": "runbook-1",
                    "title": "Test Runbook 1",
                    "success": True,
                    "error": None
                },
                {
                    "page_id": "789012",
                    "runbook_id": None,
                    "title": None,
                    "success": False,
                    "error": "Page not found"
                }
            ]
            
            request_data = {
                "page_ids": ["123456", "789012"]
            }
            
            response = client.post("/pages/bulk-extract", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_pages"] == 2
            assert data["successful_extractions"] == 1
            assert data["failed_extractions"] == 1
            assert len(data["errors"]) == 1
            assert "Page 789012: Page not found" in data["errors"][0]
    
    def test_bulk_extract_invalid_request(self, client):
        """Test bulk extraction with invalid request data."""
        request_data = {
            "page_ids": []  # Empty list should fail validation
        }
        
        response = client.post("/pages/bulk-extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation error" in str(data).lower()
    
    def test_bulk_extract_too_many_pages(self, client):
        """Test bulk extraction with too many pages."""
        # Create request with more than 100 pages (should fail validation)
        page_ids = [f"page-{i}" for i in range(101)]
        request_data = {
            "page_ids": page_ids
        }
        
        response = client.post("/pages/bulk-extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation error" in str(data).lower()


class TestErrorHandling:
    """Test cases for error handling and exception scenarios."""
    
    @patch('manager.src.tools.confluence.app.api.get_confluence_client')
    def test_confluence_client_not_configured(self, mock_get_confluence_client, client):
        """Test behavior when Confluence client is not configured."""
        mock_get_confluence_client.side_effect = HTTPException(
            status_code=500,
            detail="Confluence client not configured"
        )
        
        request_data = {
            "page_id": "123456"
        }
        
        response = client.post("/pages/extract", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Confluence client not configured" in data["detail"]
    
    @patch('manager.src.tools.confluence.app.api.get_vector_store')
    def test_vector_store_not_available(self, mock_get_vector_store, client):
        """Test behavior when vector store is not available."""
        mock_get_vector_store.side_effect = HTTPException(
            status_code=500,
            detail="Vector store not available"
        )
        
        request_data = {
            "page_id": "123456"
        }
        
        response = client.post("/pages/extract", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector store not available" in data["detail"]


class TestDependencyInjection:
    """Test cases for dependency injection functionality."""
    
    @patch('manager.src.tools.confluence.app.api.ConfluenceClient')
    def test_confluence_client_singleton(self, mock_confluence_class):
        """Test that Confluence client is created as singleton."""
        from .api import get_confluence_client
        
        # Reset global client
        import manager.src.tools.confluence.app.api as api_module
        api_module.confluence_client = None
        
        mock_instance = Mock()
        mock_confluence_class.return_value = mock_instance
        
        # Call dependency function multiple times
        client1 = get_confluence_client()
        client2 = get_confluence_client()
        
        # Should return same instance
        assert client1 is client2
        # Constructor should only be called once
        mock_confluence_class.assert_called_once()
    
    @patch('manager.src.tools.confluence.app.api.VectorStore')
    def test_vector_store_singleton(self, mock_vector_store_class):
        """Test that VectorStore is created as singleton."""
        from .api import get_vector_store
        
        # Reset global store
        import manager.src.tools.confluence.app.api as api_module
        api_module.vector_store = None
        
        mock_instance = Mock()
        mock_vector_store_class.return_value = mock_instance
        
        # Call dependency function multiple times
        store1 = get_vector_store()
        store2 = get_vector_store()
        
        # Should return same instance
        assert store1 is store2
        # Constructor should only be called once
        mock_vector_store_class.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])