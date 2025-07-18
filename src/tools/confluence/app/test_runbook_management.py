"""
Integration tests for runbook management API endpoints.

Tests the GET, PUT, DELETE, and LIST endpoints for runbook management
with proper error handling and validation.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from .api import app
from .models import (
    RunbookContent,
    RunbookMetadata,
    RunbookUpdateRequest,
    ErrorResponse
)


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_runbook_metadata():
    """Create sample runbook metadata for testing."""
    return RunbookMetadata(
        title="Test Runbook",
        author="Test Author",
        last_modified=datetime.now(),
        space_key="TEST",
        page_id="12345",
        page_url="https://confluence.example.com/pages/12345",
        tags=["test", "runbook"]
    )


@pytest.fixture
def sample_runbook_content(sample_runbook_metadata):
    """Create sample runbook content for testing."""
    return RunbookContent(
        metadata=sample_runbook_metadata,
        procedures=["Step 1: Do something", "Step 2: Do something else"],
        troubleshooting_steps=["Check logs", "Restart service"],
        prerequisites=["Access to system", "Valid credentials"],
        raw_content="This is the raw content of the runbook",
        structured_sections={"overview": "This is an overview", "details": "Detailed information"}
    )


class TestGetRunbook:
    """Test cases for GET /runbooks/{runbook_id} endpoint."""

    @patch('app.api.get_vector_store')
    def test_get_runbook_success(self, mock_get_vector_store, client, sample_runbook_content):
        """Test successful runbook retrieval."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.get(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["title"] == "Test Runbook"
        assert data["metadata"]["author"] == "Test Author"
        assert len(data["procedures"]) == 2
        assert len(data["troubleshooting_steps"]) == 2
        
        # Verify vector store was called correctly
        mock_vector_store.get_runbook_by_id.assert_called_once_with(runbook_id)

    @patch('app.api.get_vector_store')
    def test_get_runbook_not_found(self, mock_get_vector_store, client):
        """Test runbook not found scenario."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.get(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_runbook_empty_id(self, client):
        """Test empty runbook ID validation."""
        # Test with whitespace-only ID
        response = client.get("/runbooks/%20")
        assert response.status_code == 422

    @patch('app.api.get_vector_store')
    def test_get_runbook_vector_store_error(self, mock_get_vector_store, client):
        """Test vector store runtime error handling."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.side_effect = RuntimeError("Database connection failed")
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.get(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve runbook" in data["detail"]


class TestUpdateRunbook:
    """Test cases for PUT /runbooks/{runbook_id} endpoint."""

    @patch('app.api.get_vector_store')
    def test_update_runbook_success(self, mock_get_vector_store, client, sample_runbook_content):
        """Test successful runbook update."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_vector_store.update_runbook.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Prepare update request
        update_data = {
            "procedures": ["Updated step 1", "Updated step 2", "New step 3"],
            "raw_content": "Updated raw content"
        }
        
        # Make request
        response = client.put(f"/runbooks/{runbook_id}", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["procedures"]) == 3
        assert data["procedures"][0] == "Updated step 1"
        assert data["raw_content"] == "Updated raw content"
        
        # Verify vector store methods were called
        mock_vector_store.get_runbook_by_id.assert_called_once_with(runbook_id)
        mock_vector_store.update_runbook.assert_called_once()

    @patch('app.api.get_vector_store')
    def test_update_runbook_not_found(self, mock_get_vector_store, client):
        """Test updating non-existent runbook."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        update_data = {"raw_content": "Updated content"}
        
        # Make request
        response = client.put(f"/runbooks/{runbook_id}", json=update_data)
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch('app.api.get_vector_store')
    def test_update_runbook_partial_update(self, mock_get_vector_store, client, sample_runbook_content):
        """Test partial runbook update (only some fields)."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_vector_store.update_runbook.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Update only troubleshooting steps
        update_data = {
            "troubleshooting_steps": ["New troubleshooting step"]
        }
        
        # Make request
        response = client.put(f"/runbooks/{runbook_id}", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        # Original procedures should remain unchanged
        assert len(data["procedures"]) == 2
        assert data["procedures"][0] == "Step 1: Do something"
        # Troubleshooting steps should be updated
        assert len(data["troubleshooting_steps"]) == 1
        assert data["troubleshooting_steps"][0] == "New troubleshooting step"

    def test_update_runbook_empty_id(self, client):
        """Test update with empty runbook ID."""
        update_data = {"raw_content": "Updated content"}
        response = client.put("/runbooks/%20", json=update_data)
        assert response.status_code == 422

    @patch('app.api.get_vector_store')
    def test_update_runbook_validation_error(self, mock_get_vector_store, client, sample_runbook_content):
        """Test update with invalid data."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Invalid update data (empty raw content)
        update_data = {"raw_content": ""}
        
        # Make request
        response = client.put(f"/runbooks/{runbook_id}", json=update_data)
        
        # Assertions
        assert response.status_code == 422


class TestDeleteRunbook:
    """Test cases for DELETE /runbooks/{runbook_id} endpoint."""

    @patch('app.api.get_vector_store')
    def test_delete_runbook_success(self, mock_get_vector_store, client, sample_runbook_content):
        """Test successful runbook deletion."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_vector_store.delete_runbook.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.delete(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "successfully deleted" in data["message"]
        assert data["runbook_id"] == runbook_id
        assert "deleted_at" in data
        
        # Verify vector store methods were called
        mock_vector_store.get_runbook_by_id.assert_called_once_with(runbook_id)
        mock_vector_store.delete_runbook.assert_called_once_with(runbook_id)

    @patch('app.api.get_vector_store')
    def test_delete_runbook_not_found(self, mock_get_vector_store, client):
        """Test deleting non-existent runbook."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.delete(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_runbook_empty_id(self, client):
        """Test delete with empty runbook ID."""
        response = client.delete("/runbooks/%20")
        assert response.status_code == 422

    @patch('app.api.get_vector_store')
    def test_delete_runbook_vector_store_error(self, mock_get_vector_store, client, sample_runbook_content):
        """Test delete with vector store error."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_vector_store.delete_runbook.side_effect = RuntimeError("Deletion failed")
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Make request
        response = client.delete(f"/runbooks/{runbook_id}")
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to delete runbook" in data["detail"]


class TestListRunbooks:
    """Test cases for GET /runbooks endpoint."""

    @patch('app.api.get_vector_store')
    def test_list_runbooks_success(self, mock_get_vector_store, client):
        """Test successful runbook listing."""
        # Setup mock data
        mock_runbooks = [
            {
                "runbook_id": str(uuid.uuid4()),
                "title": "Runbook 1",
                "author": "Author 1",
                "space_key": "TEST",
                "page_id": "123",
                "last_modified": "2024-01-01T00:00:00",
                "chunk_count": 5
            },
            {
                "runbook_id": str(uuid.uuid4()),
                "title": "Runbook 2",
                "author": "Author 2",
                "space_key": "PROD",
                "page_id": "456",
                "last_modified": "2024-01-02T00:00:00",
                "chunk_count": 3
            }
        ]
        
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.list_runbooks.side_effect = [
            mock_runbooks,  # First call for actual results
            mock_runbooks   # Second call for total count
        ]
        mock_get_vector_store.return_value = mock_vector_store
        
        # Make request
        response = client.get("/runbooks")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["runbooks"]) == 2
        assert data["runbooks"][0]["title"] == "Runbook 1"
        assert data["runbooks"][1]["title"] == "Runbook 2"
        
        # Check pagination metadata
        assert data["pagination"]["limit"] == 20
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["total_count"] == 2
        assert data["pagination"]["returned_count"] == 2
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_previous"] is False

    @patch('app.api.get_vector_store')
    def test_list_runbooks_with_pagination(self, mock_get_vector_store, client):
        """Test runbook listing with custom pagination parameters."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.list_runbooks.side_effect = [
            [],  # Empty results for offset 10
            [{"runbook_id": "1"}, {"runbook_id": "2"}]  # Total count call
        ]
        mock_get_vector_store.return_value = mock_vector_store
        
        # Make request with pagination
        response = client.get("/runbooks?limit=5&offset=10")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 5
        assert data["pagination"]["offset"] == 10
        assert data["pagination"]["has_previous"] is True
        assert data["pagination"]["previous_offset"] == 5

    def test_list_runbooks_invalid_limit(self, client):
        """Test listing with invalid limit parameter."""
        response = client.get("/runbooks?limit=0")
        assert response.status_code == 422
        
        response = client.get("/runbooks?limit=101")
        assert response.status_code == 422

    def test_list_runbooks_invalid_offset(self, client):
        """Test listing with invalid offset parameter."""
        response = client.get("/runbooks?offset=-1")
        assert response.status_code == 422

    @patch('app.api.get_vector_store')
    def test_list_runbooks_empty_result(self, mock_get_vector_store, client):
        """Test listing when no runbooks exist."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.list_runbooks.return_value = []
        mock_get_vector_store.return_value = mock_vector_store
        
        # Make request
        response = client.get("/runbooks")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["runbooks"]) == 0
        assert data["pagination"]["total_count"] == 0
        assert data["pagination"]["returned_count"] == 0

    @patch('app.api.get_vector_store')
    def test_list_runbooks_vector_store_error(self, mock_get_vector_store, client):
        """Test listing with vector store error."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.list_runbooks.side_effect = RuntimeError("Database error")
        mock_get_vector_store.return_value = mock_vector_store
        
        # Make request
        response = client.get("/runbooks")
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to list runbooks" in data["detail"]


class TestRunbookManagementIntegration:
    """Integration tests for runbook management workflow."""

    @patch('app.api.get_vector_store')
    def test_full_runbook_lifecycle(self, mock_get_vector_store, client, sample_runbook_content):
        """Test complete runbook lifecycle: create, get, update, delete."""
        # Setup mock
        mock_vector_store = Mock()
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # 1. Get runbook (should exist for this test)
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        response = client.get(f"/runbooks/{runbook_id}")
        assert response.status_code == 200
        
        # 2. Update runbook
        mock_vector_store.update_runbook.return_value = None
        update_data = {"procedures": ["Updated procedure"]}
        response = client.put(f"/runbooks/{runbook_id}", json=update_data)
        assert response.status_code == 200
        
        # 3. List runbooks (should include our runbook)
        mock_vector_store.list_runbooks.return_value = [
            {
                "runbook_id": runbook_id,
                "title": "Test Runbook",
                "author": "Test Author",
                "space_key": "TEST",
                "page_id": "12345",
                "last_modified": "2024-01-01T00:00:00",
                "chunk_count": 3
            }
        ]
        response = client.get("/runbooks")
        assert response.status_code == 200
        assert len(response.json()["runbooks"]) == 1
        
        # 4. Delete runbook
        mock_vector_store.delete_runbook.return_value = None
        response = client.delete(f"/runbooks/{runbook_id}")
        assert response.status_code == 200
        
        # 5. Verify deletion (should return 404)
        mock_vector_store.get_runbook_by_id.return_value = None
        response = client.get(f"/runbooks/{runbook_id}")
        assert response.status_code == 404

    @patch('app.api.get_vector_store')
    def test_concurrent_runbook_operations(self, mock_get_vector_store, client, sample_runbook_content):
        """Test handling of concurrent operations on the same runbook."""
        # Setup mock
        mock_vector_store = Mock()
        mock_vector_store.get_runbook_by_id.return_value = sample_runbook_content
        mock_vector_store.update_runbook.return_value = None
        mock_get_vector_store.return_value = mock_vector_store
        
        runbook_id = str(uuid.uuid4())
        
        # Simulate concurrent updates
        update_data_1 = {"procedures": ["Concurrent update 1"]}
        update_data_2 = {"troubleshooting_steps": ["Concurrent update 2"]}
        
        response_1 = client.put(f"/runbooks/{runbook_id}", json=update_data_1)
        response_2 = client.put(f"/runbooks/{runbook_id}", json=update_data_2)
        
        # Both should succeed (in this simplified test)
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        
        # Verify both updates were attempted
        assert mock_vector_store.update_runbook.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])