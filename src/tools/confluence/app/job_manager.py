"""
Job Manager for tracking bulk extraction operations.

This module provides job tracking functionality for bulk extraction requests,
including job status management, progress tracking, and result aggregation.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import Counter

from .models import (
    BulkExtractionJob,
    PageExtractionResult,
    JobStatus,
    BulkExtractionRequest
)
from .confluence import ConfluenceClient
from .vector_store import VectorStore


class JobManager:
    """Manages bulk extraction jobs with tracking and status updates."""
    
    def __init__(self):
        """Initialize job manager with in-memory storage."""
        self._jobs: Dict[str, BulkExtractionJob] = {}
        self._lock = threading.RLock()
        self._thread_pool = ThreadPoolExecutor(max_workers=20)
    
    def create_job(self, request: BulkExtractionRequest) -> str:
        """
        Create a new bulk extraction job.
        
        Args:
            request: Bulk extraction request parameters
            
        Returns:
            str: Unique job identifier
        """
        job_id = str(uuid.uuid4())
        
        with self._lock:
            job = BulkExtractionJob(
                job_id=job_id,
                status=JobStatus.PENDING,
                created_at=datetime.utcnow(),
                total_pages=len(request.page_ids),
                concurrency_limit=request.concurrency_limit
            )
            self._jobs[job_id] = job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[BulkExtractionJob]:
        """
        Get job information by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            BulkExtractionJob or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_job_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed summary statistics for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with detailed job summary or None if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            
            # Calculate detailed statistics for this job
            summary = {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "total_pages": job.total_pages,
                "processed_pages": job.processed_pages,
                "successful_extractions": job.successful_extractions,
                "failed_extractions": job.failed_extractions,
                "processing_time": job.processing_time,
                "concurrency_limit": job.concurrency_limit,
                "success_rate": 0.0,
                "average_page_processing_time": 0.0,
                "fastest_page_time": None,
                "slowest_page_time": None,
                "error_summary": {
                    "total_errors": len(job.errors),
                    "page_errors": 0,
                    "job_errors": len(job.errors),
                    "error_types": []
                },
                "page_results_summary": []
            }
            
            # Calculate success rate
            if job.processed_pages > 0:
                summary["success_rate"] = round(
                    (job.successful_extractions / job.processed_pages) * 100, 2
                )
            
            # Analyze page processing times and errors
            page_times = []
            error_types = {}
            
            for result in job.page_results:
                if result.processing_time > 0:
                    page_times.append(result.processing_time)
                
                if not result.success and result.error:
                    summary["error_summary"]["page_errors"] += 1
                    # Categorize error types
                    error_key = result.error.split(':')[0].strip() if ':' in result.error else result.error[:50]
                    error_types[error_key] = error_types.get(error_key, 0) + 1
                
                # Add page result summary
                summary["page_results_summary"].append({
                    "page_id": result.page_id,
                    "title": result.title,
                    "success": result.success,
                    "processing_time": result.processing_time,
                    "error": result.error if not result.success else None
                })
            
            # Calculate page processing time statistics
            if page_times:
                summary["average_page_processing_time"] = round(
                    sum(page_times) / len(page_times), 2
                )
                summary["fastest_page_time"] = round(min(page_times), 2)
                summary["slowest_page_time"] = round(max(page_times), 2)
            
            # Add error type analysis
            summary["error_summary"]["error_types"] = [
                {"error_type": error_type, "count": count}
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)
            ]
            
            return summary
    
    def update_job_status(self, job_id: str, status: str) -> None:
        """
        Update job status.
        
        Args:
            job_id: Job identifier
            status: New job status
        """
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = status
                
                if status == JobStatus.RUNNING and job.started_at is None:
                    job.started_at = datetime.utcnow()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = datetime.utcnow()
                    if job.started_at:
                        job.processing_time = (job.completed_at - job.started_at).total_seconds()
    
    def add_page_result(self, job_id: str, result: PageExtractionResult) -> None:
        """
        Add a page extraction result to the job.
        
        Args:
            job_id: Job identifier
            result: Page extraction result
        """
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.page_results.append(result)
                job.processed_pages += 1
                
                if result.success:
                    job.successful_extractions += 1
                else:
                    job.failed_extractions += 1
    
    def add_job_error(self, job_id: str, error: str) -> None:
        """
        Add a general error message to the job.
        
        Args:
            job_id: Job identifier
            error: Error message
        """
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.errors.append(error)
    
    def list_jobs(self, limit: int = 50, offset: int = 0) -> List[BulkExtractionJob]:
        """
        List all jobs with pagination.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of jobs
        """
        with self._lock:
            jobs = list(self._jobs.values())
            # Sort by creation time, newest first
            jobs.sort(key=lambda x: x.created_at, reverse=True)
            return jobs[offset:offset + limit]
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        with self._lock:
            jobs_to_remove = []
            for job_id, job in self._jobs.items():
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                    job.completed_at and job.completed_at.timestamp() < cutoff_time):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                cleaned_count += 1
        
        return cleaned_count
    
    def get_job_statistics(self) -> dict:
        """
        Get overall job statistics.
        
        Returns:
            Dictionary with comprehensive job statistics
        """
        with self._lock:
            stats = {
                "total_jobs": len(self._jobs),
                "pending_jobs": 0,
                "running_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "cancelled_jobs": 0,
                "total_pages_processed": 0,
                "total_successful_extractions": 0,
                "total_failed_extractions": 0,
                "average_processing_time": 0.0,
                "total_processing_time": 0.0,
                "average_pages_per_job": 0.0,
                "success_rate_percentage": 0.0,
                "most_common_errors": [],
                "performance_metrics": {
                    "fastest_job_time": None,
                    "slowest_job_time": None,
                    "average_page_processing_time": 0.0
                }
            }
            
            processing_times = []
            all_errors = []
            page_processing_times = []
            
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    stats["pending_jobs"] += 1
                elif job.status == JobStatus.RUNNING:
                    stats["running_jobs"] += 1
                elif job.status == JobStatus.COMPLETED:
                    stats["completed_jobs"] += 1
                elif job.status == JobStatus.FAILED:
                    stats["failed_jobs"] += 1
                elif job.status == JobStatus.CANCELLED:
                    stats["cancelled_jobs"] += 1
                
                stats["total_pages_processed"] += job.processed_pages
                stats["total_successful_extractions"] += job.successful_extractions
                stats["total_failed_extractions"] += job.failed_extractions
                
                # Collect processing times for averages
                if job.processing_time is not None:
                    processing_times.append(job.processing_time)
                    stats["total_processing_time"] += job.processing_time
                
                # Collect errors for analysis
                all_errors.extend(job.errors)
                for result in job.page_results:
                    if not result.success and result.error:
                        all_errors.append(result.error)
                    if result.processing_time > 0:
                        page_processing_times.append(result.processing_time)
            
            # Calculate averages and performance metrics
            if len(self._jobs) > 0:
                stats["average_pages_per_job"] = round(
                    stats["total_pages_processed"] / len(self._jobs), 2
                )
            
            if processing_times:
                stats["average_processing_time"] = round(
                    sum(processing_times) / len(processing_times), 2
                )
                stats["performance_metrics"]["fastest_job_time"] = round(min(processing_times), 2)
                stats["performance_metrics"]["slowest_job_time"] = round(max(processing_times), 2)
            
            if page_processing_times:
                stats["performance_metrics"]["average_page_processing_time"] = round(
                    sum(page_processing_times) / len(page_processing_times), 2
                )
            
            # Calculate success rate
            total_extractions = stats["total_successful_extractions"] + stats["total_failed_extractions"]
            if total_extractions > 0:
                stats["success_rate_percentage"] = round(
                    (stats["total_successful_extractions"] / total_extractions) * 100, 2
                )
            
            # Analyze most common errors
            if all_errors:
                error_counts = Counter(all_errors)
                stats["most_common_errors"] = [
                    {"error": error, "count": count}
                    for error, count in error_counts.most_common(5)
                ]
            
            return stats
    
    async def execute_bulk_extraction(
        self,
        job_id: str,
        page_ids: List[str],
        confluence_client: ConfluenceClient,
        vector_store: VectorStore,
        concurrency_limit: int = 5
    ) -> None:
        """
        Execute bulk extraction job asynchronously.
        
        Args:
            job_id: Job identifier
            page_ids: List of page IDs to extract
            confluence_client: Confluence client instance
            vector_store: Vector store instance
            concurrency_limit: Maximum concurrent extractions
        """
        self.update_job_status(job_id, JobStatus.RUNNING)
        
        try:
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(concurrency_limit)
            
            # Create tasks for parallel processing
            tasks = []
            for page_id in page_ids:
                # Check if job was cancelled before creating new tasks
                job = self.get_job(job_id)
                if job and job.status == JobStatus.CANCELLED:
                    break
                    
                task = self._extract_single_page_async(
                    job_id, page_id, confluence_client, vector_store, semaphore
                )
                tasks.append(task)
            
            # Wait for all tasks to complete, handling cancellation
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any exceptions that occurred
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.add_job_error(job_id, f"Task {i} failed: {str(result)}")
            
            # Update final job status
            job = self.get_job(job_id)
            if job:
                if job.status == JobStatus.CANCELLED:
                    # Job was cancelled during execution
                    pass  # Keep cancelled status
                elif job.failed_extractions == 0 and job.successful_extractions > 0:
                    self.update_job_status(job_id, JobStatus.COMPLETED)
                elif job.successful_extractions > 0:
                    # Partial success - still mark as completed
                    self.update_job_status(job_id, JobStatus.COMPLETED)
                else:
                    # No successful extractions
                    self.update_job_status(job_id, JobStatus.FAILED)
                    
        except Exception as e:
            self.add_job_error(job_id, f"Bulk extraction failed: {str(e)}")
            self.update_job_status(job_id, JobStatus.FAILED)
    
    async def _extract_single_page_async(
        self,
        job_id: str,
        page_id: str,
        confluence_client: ConfluenceClient,
        vector_store: VectorStore,
        semaphore: asyncio.Semaphore
    ) -> None:
        """
        Extract a single page asynchronously with concurrency control.
        
        Args:
            job_id: Job identifier
            page_id: Page ID to extract
            confluence_client: Confluence client instance
            vector_store: Vector store instance
            semaphore: Semaphore for concurrency control
        """
        async with semaphore:
            start_time = datetime.utcnow()
            
            try:
                # Check if job was cancelled before starting extraction
                job = self.get_job(job_id)
                if job and job.status == JobStatus.CANCELLED:
                    result = PageExtractionResult(
                        page_id=page_id,
                        runbook_id=None,
                        title=None,
                        success=False,
                        error="Job was cancelled before extraction started",
                        processing_time=0.0
                    )
                    self.add_page_result(job_id, result)
                    return
                
                # Run extraction in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                
                # Create a wrapper that checks for cancellation during execution
                async def cancellable_extraction():
                    # Check for cancellation before starting
                    job = self.get_job(job_id)
                    if job and job.status == JobStatus.CANCELLED:
                        return {
                            "page_id": page_id,
                            "runbook_id": None,
                            "title": None,
                            "success": False,
                            "error": "Job was cancelled during extraction"
                        }
                    
                    # Run the actual extraction
                    return await loop.run_in_executor(
                        self._thread_pool,
                        self._extract_single_page_sync,
                        page_id,
                        confluence_client,
                        vector_store
                    )
                
                result_dict = await cancellable_extraction()
                
                # Calculate processing time
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                # Final check if job was cancelled during extraction
                job = self.get_job(job_id)
                if job and job.status == JobStatus.CANCELLED and result_dict.get("success", False):
                    result = PageExtractionResult(
                        page_id=page_id,
                        runbook_id=None,
                        title=None,
                        success=False,
                        error="Job was cancelled during extraction",
                        processing_time=processing_time
                    )
                    self.add_page_result(job_id, result)
                    return
                
                # Create result object
                result = PageExtractionResult(
                    page_id=page_id,
                    runbook_id=result_dict.get("runbook_id"),
                    title=result_dict.get("title"),
                    success=result_dict.get("success", False),
                    error=result_dict.get("error"),
                    processing_time=processing_time
                )
                
                # Add result to job
                self.add_page_result(job_id, result)
                
            except Exception as e:
                # Calculate processing time even for failures
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                # Check if the exception was due to cancellation
                job = self.get_job(job_id)
                if job and job.status == JobStatus.CANCELLED:
                    error_msg = "Job was cancelled during extraction"
                else:
                    error_msg = f"Extraction failed: {str(e)}"
                
                result = PageExtractionResult(
                    page_id=page_id,
                    runbook_id=None,
                    title=None,
                    success=False,
                    error=error_msg,
                    processing_time=processing_time
                )
                
                self.add_page_result(job_id, result)
    
    def _extract_single_page_sync(
        self,
        page_id: str,
        confluence_client: ConfluenceClient,
        vector_store: VectorStore
    ) -> Dict[str, Any]:
        """
        Synchronous single page extraction (runs in thread pool).
        
        Args:
            page_id: Page ID to extract
            confluence_client: Confluence client instance
            vector_store: Vector store instance
            
        Returns:
            Dictionary with extraction result
        """
        try:
            # Get page content
            page_data = confluence_client.get_page_by_id(page_id)
            
            # Extract runbook content
            runbook_content = confluence_client.extract_runbook_content(page_data)
            
            # Store in vector database
            runbook_id = vector_store.add_runbook(runbook_content)
            
            return {
                "page_id": page_id,
                "runbook_id": runbook_id,
                "title": runbook_content.metadata.title,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "page_id": page_id,
                "runbook_id": None,
                "title": None,
                "success": False,
                "error": str(e)
            }


# Global job manager instance
job_manager = JobManager()