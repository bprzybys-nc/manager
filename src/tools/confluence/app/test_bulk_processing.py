"""
Integration tests for bulk processing with job tracking functionality.

Tests the complete bulk extraction workflow including job creation,
parallel processing, status tracking, and error handling.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import List, Dict, Any

from fastapi.testclient import TestClient
from fastapi import BackgroundTasks

from .api import app
from .job_manager import job_manager, JobManager
from .models import (
    BulkExtractionRequest,
    BulkExtractionJob,
    PageExtractionResult,
    JobStatus,
    RunbookContent,
    RunbookMetadata
)
from .confluence import ConfluenceClient
from .vector_store import VectorStore


class TestBulkProcessingIntegration:
    """Integration tests for bulk processing with job tracking."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_confluence_client(self):
        """Mock Confluence client for testing."""
        mock_client = Mock(spec=ConfluenceClient)
        
        # Mock successful page extraction
        mock_page_data = {
            "id": "123456",
            "title": "Test Runbook",
            "space": {"key": "TEST", "name": "Test Space"},
            "version": {
                "when": "2024-01-01T00:00:00.000Z",
                "by": {"displayName": "Test User"}
            },
            "body": {
                "storage": {
                    "value": "<h1>Test Runbook</h1><p>Test procedure content</p>"
                }
            }
        }
        
        mock_client.get_page_by_id.return_value = mock_page_data
        
        # Mock runbook content extraction
        mock_runbook_content = RunbookContent(
            metadata=RunbookMetadata(
                title="Test Runbook",
                author="Test User",
                last_modified=datetime.utcnow(),
                space_key="TEST",
                page_id="123456",
                page_url="https://test.atlassian.net/wiki/spaces/TEST/pages/123456",
                tags=["test"]
            ),
            procedures=["Step 1: Test procedure"],
            troubleshooting_steps=["Check test configuration"],
            prerequisites=["Test environment"],
            raw_content="Test Runbook\nTest procedure content",
            structured_sections={"procedures": "Step 1: Test procedure"}
        )
        
        mock_client.extract_runbook_content.return_value = mock_runbook_content
        
        return mock_client
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store for testing."""
        mock_store = Mock(spec=VectorStore)
        mock_store.add_runbook.return_value = "runbook_123"
        return mock_store
    
    @pytest.fixture
    def fresh_job_manager(self):
        """Create a fresh job manager for each test."""
        return JobManager()
    
    def test_create_bulk_extraction_job(self, fresh_job_manager):
        """Test job creation for bulk extraction."""
        request = BulkExtractionRequest(
            page_ids=["123", "456", "789"],
            concurrency_limit=3
        )
        
        job_id = fresh_job_manager.create_job(request)
        
        assert job_id is not None
        assert len(job_id) > 0
        
        job = fresh_job_manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.PENDING
        assert job.total_pages == 3
        assert job.concurrency_limit == 3
        assert job.processed_pages == 0
        assert job.successful_extractions == 0
        assert job.failed_extractions == 0
    
    def test_job_status_updates(self, fresh_job_manager):
        """Test job status update functionality."""
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = fresh_job_manager.create_job(request)
        
        # Test status progression
        fresh_job_manager.update_job_status(job_id, JobStatus.RUNNING)
        job = fresh_job_manager.get_job(job_id)
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
        
        fresh_job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        job = fresh_job_manager.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.processing_time is not None
        assert job.processing_time >= 0
    
    def test_add_page_results(self, fresh_job_manager):
        """Test adding page extraction results to job."""
        request = BulkExtractionRequest(page_ids=["123", "456"])
        job_id = fresh_job_manager.create_job(request)
        
        # Add successful result
        success_result = PageExtractionResult(
            page_id="123",
            runbook_id="runbook_123",
            title="Test Runbook",
            success=True,
            error=None,
            processing_time=1.5
        )
        fresh_job_manager.add_page_result(job_id, success_result)
        
        # Add failed result
        failure_result = PageExtractionResult(
            page_id="456",
            runbook_id=None,
            title=None,
            success=False,
            error="Page not found",
            processing_time=0.5
        )
        fresh_job_manager.add_page_result(job_id, failure_result)
        
        job = fresh_job_manager.get_job(job_id)
        assert job.processed_pages == 2
        assert job.successful_extractions == 1
        assert job.failed_extractions == 1
        assert len(job.page_results) == 2
        
        # Verify result details
        assert job.page_results[0].page_id == "123"
        assert job.page_results[0].success is True
        assert job.page_results[1].page_id == "456"
        assert job.page_results[1].success is False
    
    def test_job_error_handling(self, fresh_job_manager):
        """Test job error message handling."""
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = fresh_job_manager.create_job(request)
        
        fresh_job_manager.add_job_error(job_id, "Connection timeout")
        fresh_job_manager.add_job_error(job_id, "Rate limit exceeded")
        
        job = fresh_job_manager.get_job(job_id)
        assert len(job.errors) == 2
        assert "Connection timeout" in job.errors
        assert "Rate limit exceeded" in job.errors
    
    def test_list_jobs_pagination(self, fresh_job_manager):
        """Test job listing with pagination."""
        # Create multiple jobs
        job_ids = []
        for i in range(5):
            request = BulkExtractionRequest(page_ids=[f"page_{i}"])
            job_id = fresh_job_manager.create_job(request)
            job_ids.append(job_id)
        
        # Test pagination
        jobs_page1 = fresh_job_manager.list_jobs(limit=3, offset=0)
        assert len(jobs_page1) == 3
        
        jobs_page2 = fresh_job_manager.list_jobs(limit=3, offset=3)
        assert len(jobs_page2) == 2
        
        # Verify no overlap
        page1_ids = {job.job_id for job in jobs_page1}
        page2_ids = {job.job_id for job in jobs_page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
    
    @pytest.mark.asyncio
    async def test_bulk_extraction_execution(self, fresh_job_manager, mock_confluence_client, mock_vector_store):
        """Test complete bulk extraction execution."""
        page_ids = ["123", "456", "789"]
        job_id = fresh_job_manager.create_job(
            BulkExtractionRequest(page_ids=page_ids, concurrency_limit=2)
        )
        
        # Execute bulk extraction
        await fresh_job_manager.execute_bulk_extraction(
            job_id=job_id,
            page_ids=page_ids,
            confluence_client=mock_confluence_client,
            vector_store=mock_vector_store,
            concurrency_limit=2
        )
        
        # Verify job completion
        job = fresh_job_manager.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.processed_pages == 3
        assert job.successful_extractions == 3
        assert job.failed_extractions == 0
        assert len(job.page_results) == 3
        
        # Verify all pages were processed
        processed_page_ids = {result.page_id for result in job.page_results}
        assert processed_page_ids == set(page_ids)
        
        # Verify Confluence client was called for each page
        assert mock_confluence_client.get_page_by_id.call_count == 3
        assert mock_confluence_client.extract_runbook_content.call_count == 3
        assert mock_vector_store.add_runbook.call_count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_extraction_with_failures(self, fresh_job_manager, mock_vector_store):
        """Test bulk extraction with some page failures."""
        mock_confluence_client = Mock(spec=ConfluenceClient)
        
        def mock_get_page_by_id(page_id):
            if page_id == "404":
                raise Exception("Page not found")
            return {
                "id": page_id,
                "title": f"Test Page {page_id}",
                "space": {"key": "TEST"},
                "version": {"when": "2024-01-01T00:00:00.000Z"},
                "body": {"storage": {"value": f"<p>Content for {page_id}</p>"}}
            }
        
        mock_confluence_client.get_page_by_id.side_effect = mock_get_page_by_id
        mock_confluence_client.extract_runbook_content.return_value = RunbookContent(
            metadata=RunbookMetadata(
                title="Test",
                last_modified=datetime.utcnow(),
                space_key="TEST",
                page_id="123",
                page_url="https://test.com",
            ),
            raw_content="Test content"
        )
        
        page_ids = ["123", "404", "789"]
        job_id = fresh_job_manager.create_job(
            BulkExtractionRequest(page_ids=page_ids, concurrency_limit=2)
        )
        
        # Execute bulk extraction
        await fresh_job_manager.execute_bulk_extraction(
            job_id=job_id,
            page_ids=page_ids,
            confluence_client=mock_confluence_client,
            vector_store=mock_vector_store,
            concurrency_limit=2
        )
        
        # Verify mixed results
        job = fresh_job_manager.get_job(job_id)
        assert job.status == JobStatus.COMPLETED  # Should complete even with failures
        assert job.processed_pages == 3
        assert job.successful_extractions == 2
        assert job.failed_extractions == 1
        
        # Find the failed result
        failed_results = [r for r in job.page_results if not r.success]
        assert len(failed_results) == 1
        assert failed_results[0].page_id == "404"
        assert "Page not found" in failed_results[0].error
    
    @pytest.mark.asyncio
    async def test_concurrency_limiting(self, fresh_job_manager, mock_vector_store):
        """Test that concurrency limits are respected."""
        mock_confluence_client = Mock(spec=ConfluenceClient)
        
        # Track concurrent calls
        active_calls = []
        max_concurrent = 0
        
        async def mock_get_page_by_id(page_id):
            active_calls.append(page_id)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, len(active_calls))
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            active_calls.remove(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "space": {"key": "TEST"},
                "version": {"when": "2024-01-01T00:00:00.000Z"},
                "body": {"storage": {"value": f"Content {page_id}"}}
            }
        
        mock_confluence_client.get_page_by_id.side_effect = mock_get_page_by_id
        mock_confluence_client.extract_runbook_content.return_value = RunbookContent(
            metadata=RunbookMetadata(
                title="Test",
                last_modified=datetime.utcnow(),
                space_key="TEST",
                page_id="123",
                page_url="https://test.com",
            ),
            raw_content="Test content"
        )
        
        page_ids = [f"page_{i}" for i in range(10)]
        concurrency_limit = 3
        
        job_id = fresh_job_manager.create_job(
            BulkExtractionRequest(page_ids=page_ids, concurrency_limit=concurrency_limit)
        )
        
        # Execute bulk extraction
        await fresh_job_manager.execute_bulk_extraction(
            job_id=job_id,
            page_ids=page_ids,
            confluence_client=mock_confluence_client,
            vector_store=mock_vector_store,
            concurrency_limit=concurrency_limit
        )
        
        # Verify concurrency was limited
        assert max_concurrent <= concurrency_limit
        
        # Verify all pages were processed
        job = fresh_job_manager.get_job(job_id)
        assert job.processed_pages == 10
        assert job.successful_extractions == 10
    
    def test_cleanup_old_jobs(self, fresh_job_manager):
        """Test cleanup of old completed jobs."""
        # Create some jobs and mark them as completed
        old_job_ids = []
        for i in range(3):
            request = BulkExtractionRequest(page_ids=[f"page_{i}"])
            job_id = fresh_job_manager.create_job(request)
            old_job_ids.append(job_id)
            
            # Mark as completed and set old completion time
            fresh_job_manager.update_job_status(job_id, JobStatus.COMPLETED)
            job = fresh_job_manager.get_job(job_id)
            # Manually set old completion time (25 hours ago)
            job.completed_at = datetime.fromtimestamp(datetime.utcnow().timestamp() - 25 * 3600)
        
        # Create a recent job
        recent_request = BulkExtractionRequest(page_ids=["recent_page"])
        recent_job_id = fresh_job_manager.create_job(recent_request)
        fresh_job_manager.update_job_status(recent_job_id, JobStatus.COMPLETED)
        
        # Cleanup old jobs (max age 24 hours)
        cleaned_count = fresh_job_manager.cleanup_old_jobs(max_age_hours=24)
        
        assert cleaned_count == 3
        
        # Verify old jobs are gone
        for job_id in old_job_ids:
            assert fresh_job_manager.get_job(job_id) is None
        
        # Verify recent job is still there
        assert fresh_job_manager.get_job(recent_job_id) is not None
    
    @pytest.mark.asyncio
    async def test_job_cancellation_during_execution(self, fresh_job_manager, mock_vector_store):
        """Test that jobs can be cancelled during execution."""
        mock_confluence_client = Mock(spec=ConfluenceClient)
        
        # Mock a slow extraction process (synchronous since it runs in thread pool)
        def slow_get_page_by_id(page_id):
            # Simulate slow processing
            import time
            time.sleep(0.2)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "space": {"key": "TEST"},
                "version": {"when": "2024-01-01T00:00:00.000Z"},
                "body": {"storage": {"value": f"Content {page_id}"}}
            }
        
        mock_confluence_client.get_page_by_id.side_effect = slow_get_page_by_id
        mock_confluence_client.extract_runbook_content.return_value = RunbookContent(
            metadata=RunbookMetadata(
                title="Test",
                last_modified=datetime.utcnow(),
                space_key="TEST",
                page_id="123",
                page_url="https://test.com",
            ),
            raw_content="Test content"
        )
        
        page_ids = [f"page_{i}" for i in range(5)]
        job_id = fresh_job_manager.create_job(
            BulkExtractionRequest(page_ids=page_ids, concurrency_limit=2)
        )
        
        # Start extraction in background
        extraction_task = asyncio.create_task(
            fresh_job_manager.execute_bulk_extraction(
                job_id=job_id,
                page_ids=page_ids,
                confluence_client=mock_confluence_client,
                vector_store=mock_vector_store,
                concurrency_limit=2
            )
        )
        
        # Wait a bit for extraction to start
        await asyncio.sleep(0.1)
        
        # Cancel the job
        fresh_job_manager.update_job_status(job_id, JobStatus.CANCELLED)
        
        # Wait for extraction to complete
        await extraction_task
        
        # Verify job was cancelled
        job = fresh_job_manager.get_job(job_id)
        assert job.status == JobStatus.CANCELLED
        
        # Some pages might have been processed before cancellation
        assert job.processed_pages <= len(page_ids)
        
        # Check that cancelled pages have appropriate error messages
        # Since we cancelled during execution, we should have at least some cancelled results
        cancelled_results = [r for r in job.page_results if not r.success and "cancelled" in r.error.lower()]
        
        # We should have at least one cancelled result since we cancelled during execution
        assert len(cancelled_results) > 0
    
    def test_get_job_statistics(self, fresh_job_manager):
        """Test job statistics functionality."""
        # Create jobs with different statuses
        request1 = BulkExtractionRequest(page_ids=["123", "456"])
        job_id1 = fresh_job_manager.create_job(request1)
        fresh_job_manager.update_job_status(job_id1, JobStatus.COMPLETED)
        fresh_job_manager.add_page_result(job_id1, PageExtractionResult(
            page_id="123", success=True, processing_time=1.0
        ))
        fresh_job_manager.add_page_result(job_id1, PageExtractionResult(
            page_id="456", success=False, error="Test error", processing_time=0.5
        ))
        
        request2 = BulkExtractionRequest(page_ids=["789"])
        job_id2 = fresh_job_manager.create_job(request2)
        fresh_job_manager.update_job_status(job_id2, JobStatus.RUNNING)
        
        request3 = BulkExtractionRequest(page_ids=["000"])
        job_id3 = fresh_job_manager.create_job(request3)
        # Leave as pending
        
        # Get statistics
        stats = fresh_job_manager.get_job_statistics()
        
        assert stats["total_jobs"] == 3
        assert stats["pending_jobs"] == 1
        assert stats["running_jobs"] == 1
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 0
        assert stats["cancelled_jobs"] == 0
        assert stats["total_pages_processed"] == 2
        assert stats["total_successful_extractions"] == 1
        assert stats["total_failed_extractions"] == 1


class TestBulkProcessingAPI:
    """Test the API endpoints for bulk processing."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('app.api.get_confluence_client')
    @patch('app.api.get_vector_store')
    def test_bulk_extract_api_endpoint(self, mock_get_vector_store, mock_get_confluence_client, client):
        """Test the bulk extraction API endpoint."""
        # Setup mocks
        mock_confluence_client = Mock()
        mock_vector_store = Mock()
        mock_get_confluence_client.return_value = mock_confluence_client
        mock_get_vector_store.return_value = mock_vector_store
        
        # Test request
        request_data = {
            "page_ids": ["123", "456", "789"],
            "concurrency_limit": 3
        }
        
        response = client.post("/pages/bulk-extract", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["total_pages"] == 3
        assert data["successful_extractions"] == 0
        assert data["failed_extractions"] == 0
        assert data["processing_time"] is None
        assert data["errors"] == []
    
    def test_get_job_statistics_api(self, client):
        """Test the job statistics API endpoint."""
        # Clear existing jobs and create test jobs
        job_manager._jobs.clear()
        
        # Create jobs with different statuses
        request1 = BulkExtractionRequest(page_ids=["123"])
        job_id1 = job_manager.create_job(request1)
        job_manager.update_job_status(job_id1, JobStatus.COMPLETED)
        job_manager.add_page_result(job_id1, PageExtractionResult(
            page_id="123", success=True, processing_time=1.0
        ))
        
        request2 = BulkExtractionRequest(page_ids=["456"])
        job_id2 = job_manager.create_job(request2)
        job_manager.update_job_status(job_id2, JobStatus.FAILED)
        job_manager.add_page_result(job_id2, PageExtractionResult(
            page_id="456", success=False, error="Test error", processing_time=0.5
        ))
        
        # Test getting statistics
        response = client.get("/jobs/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_jobs"] == 2
        assert data["completed_jobs"] == 1
        assert data["failed_jobs"] == 1
        assert data["total_successful_extractions"] == 1
        assert data["total_failed_extractions"] == 1
        assert data["success_rate"] == 50.0
        assert "generated_at" in data
    
    def test_cleanup_jobs_api(self, client):
        """Test the cleanup jobs API endpoint."""
        # Clear existing jobs
        job_manager._jobs.clear()
        
        # Create an old completed job
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = job_manager.create_job(request)
        job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        # Manually set old completion time
        job = job_manager.get_job(job_id)
        job.completed_at = datetime.fromtimestamp(datetime.utcnow().timestamp() - 25 * 3600)
        
        # Test cleanup
        response = client.post("/jobs/cleanup?max_age_hours=24")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cleaned_jobs"] == 1
        assert data["max_age_hours"] == 24
        assert "cleaned_at" in data
        
        # Verify job was removed
        assert job_manager.get_job(job_id) is None
    
    def test_cleanup_jobs_validation(self, client):
        """Test cleanup jobs API validation."""
        # Test invalid max_age_hours
        response = client.post("/jobs/cleanup?max_age_hours=0")
        assert response.status_code == 422
        
        response = client.post("/jobs/cleanup?max_age_hours=200")
        assert response.status_code == 422
    
    def test_get_job_status_api(self, client):
        """Test the job status API endpoint."""
        # Create a job first
        job_manager._jobs.clear()  # Clear any existing jobs
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = job_manager.create_job(request)
        
        # Test getting job status
        response = client.get(f"/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["total_pages"] == 1
    
    def test_get_nonexistent_job(self, client):
        """Test getting status of non-existent job."""
        response = client.get("/jobs/nonexistent-job-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_list_jobs_api(self, client):
        """Test the list jobs API endpoint."""
        # Clear existing jobs and create test jobs
        job_manager._jobs.clear()
        
        job_ids = []
        for i in range(3):
            request = BulkExtractionRequest(page_ids=[f"page_{i}"])
            job_id = job_manager.create_job(request)
            job_ids.append(job_id)
        
        # Test listing jobs
        response = client.get("/jobs?limit=2&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "pagination" in data
        assert len(data["jobs"]) == 2
        assert data["pagination"]["total_count"] == 3
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["offset"] == 0
    
    def test_cancel_job_api(self, client):
        """Test the cancel job API endpoint."""
        # Create a job
        job_manager._jobs.clear()
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = job_manager.create_job(request)
        
        # Test cancelling job
        response = client.delete(f"/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert "cancelled" in data["message"].lower()
        
        # Verify job status was updated
        job = job_manager.get_job(job_id)
        assert job.status == "cancelled"
    
    def test_cancel_completed_job(self, client):
        """Test cancelling a completed job (should fail)."""
        # Create and complete a job
        job_manager._jobs.clear()
        request = BulkExtractionRequest(page_ids=["123"])
        job_id = job_manager.create_job(request)
        job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        # Test cancelling completed job
        response = client.delete(f"/jobs/{job_id}")
        
        assert response.status_code == 409
        assert "cannot be cancelled" in response.json()["detail"].lower()
    
    def test_invalid_bulk_extraction_request(self, client):
        """Test bulk extraction with invalid request data."""
        # Test empty page_ids
        response = client.post("/pages/bulk-extract", json={"page_ids": []})
        assert response.status_code == 422
        
        # Test too many page_ids
        response = client.post("/pages/bulk-extract", json={
            "page_ids": [f"page_{i}" for i in range(101)]
        })
        assert response.status_code == 422
        
        # Test invalid concurrency_limit
        response = client.post("/pages/bulk-extract", json={
            "page_ids": ["123"],
            "concurrency_limit": 0
        })
        assert response.status_code == 422
    
    def test_get_job_summary_api(self, client):
        """Test the job summary API endpoint."""
        # Clear existing jobs and create test job
        job_manager._jobs.clear()
        
        # Create a job with mixed results
        request = BulkExtractionRequest(page_ids=["123", "456", "789"])
        job_id = job_manager.create_job(request)
        job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        # Add page results with different outcomes
        job_manager.add_page_result(job_id, PageExtractionResult(
            page_id="123", runbook_id="rb_123", title="Success Page", 
            success=True, processing_time=1.5
        ))
        job_manager.add_page_result(job_id, PageExtractionResult(
            page_id="456", success=False, error="Page not found", processing_time=0.8
        ))
        job_manager.add_page_result(job_id, PageExtractionResult(
            page_id="789", runbook_id="rb_789", title="Another Success", 
            success=True, processing_time=2.1
        ))
        
        # Test getting job summary
        response = client.get(f"/jobs/{job_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary structure and content
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["total_pages"] == 3
        assert data["processed_pages"] == 3
        assert data["successful_extractions"] == 2
        assert data["failed_extractions"] == 1
        assert data["success_rate"] == 66.67
        assert data["average_page_processing_time"] == 1.47  # (1.5 + 0.8 + 2.1) / 3
        assert data["fastest_page_time"] == 0.8
        assert data["slowest_page_time"] == 2.1
        
        # Verify error summary
        assert data["error_summary"]["total_errors"] == 0  # No job-level errors
        assert data["error_summary"]["page_errors"] == 1
        assert len(data["error_summary"]["error_types"]) == 1
        assert data["error_summary"]["error_types"][0]["error_type"] == "Page not found"
        assert data["error_summary"]["error_types"][0]["count"] == 1
        
        # Verify page results summary
        assert len(data["page_results_summary"]) == 3
        page_results = {r["page_id"]: r for r in data["page_results_summary"]}
        
        assert page_results["123"]["success"] is True
        assert page_results["123"]["title"] == "Success Page"
        assert page_results["456"]["success"] is False
        assert page_results["456"]["error"] == "Page not found"
        assert page_results["789"]["success"] is True
    
    def test_get_nonexistent_job_summary(self, client):
        """Test getting summary of non-existent job."""
        response = client.get("/jobs/nonexistent-job-id/summary")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_job_api_validation(self, client):
        """Test API validation for job endpoints."""
        # Test invalid pagination parameters
        response = client.get("/jobs?limit=0")
        assert response.status_code == 422
        
        response = client.get("/jobs?offset=-1")
        assert response.status_code == 422
        
        response = client.get("/jobs?limit=101")
        assert response.status_code == 422
        
        # Test invalid job ID format (empty string after jobs/)
        response = client.get("/jobs/ ")  # Space after slash
        assert response.status_code == 422
        
        # Test invalid job ID for summary endpoint
        response = client.get("/jobs/ /summary")  # Space in job ID
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])