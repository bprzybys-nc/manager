"""FastAPI application for Confluence Integration Tool."""

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from .confluence import ConfluenceClient, ConfluenceAPIError
from .vector_store import VectorStore
from .job_manager import job_manager
from .error_handler import (
    StructuredLogger,
    ErrorHandler,
    validate_environment_variables,
    create_error_response
)
from .models import (
    PageExtractionRequest,
    BulkExtractionRequest,
    BulkExtractionResponse,
    BulkExtractionJob,
    RunbookContent,
    ErrorResponse,
    ConfluenceSearchRequest,
    RunbookSearchRequest,
    RunbookSearchResponse,
    SearchResult,
    RunbookUpdateRequest,
    HealthResponse
)

app = FastAPI(
    title="Confluence Integration Tool",
    version="0.1.0",
    description="AI-powered Confluence runbook extraction and vector search service"
)

# Global instances
confluence_client = None
vector_store = None
thread_pool = ThreadPoolExecutor(max_workers=5)
logger = StructuredLogger(__name__)
error_handler = ErrorHandler(logger)

@app.on_event("startup")
async def startup_event():
    """Validate environment and initialize services on startup."""
    try:
        # Validate required environment variables
        required_vars = {
            "CONFLUENCE_URL": "Confluence server URL",
            "CONFLUENCE_USERNAME": "Confluence username/email",
            "CONFLUENCE_API_TOKEN": "Confluence API token"
        }
        
        validate_environment_variables(required_vars)
        logger.info("Environment validation successful")
        
        # Initialize global instances to validate connectivity
        global confluence_client, vector_store
        
        try:
            confluence_client = ConfluenceClient()
            logger.info("Confluence client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Confluence client", error=str(e))
            # Don't fail startup, but log the error
        
        try:
            vector_store = VectorStore()
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize vector store", error=str(e))
            # Don't fail startup, but log the error
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise

def get_confluence_client() -> ConfluenceClient:
    """Dependency to get Confluence client instance."""
    global confluence_client
    if confluence_client is None:
        try:
            confluence_client = ConfluenceClient()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Confluence client not configured: {str(e)}"
            )
    return confluence_client

def get_vector_store() -> VectorStore:
    """Dependency to get VectorStore instance."""
    global vector_store
    if vector_store is None:
        try:
            vector_store = VectorStore()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Vector store not available: {str(e)}"
            )
    return vector_store

def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID for request tracking."""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id

@app.exception_handler(ConfluenceAPIError)
async def confluence_api_error_handler(request: Request, exc: ConfluenceAPIError):
    """Handle Confluence API errors with proper HTTP status codes."""
    correlation_id = get_correlation_id(request)
    
    with logger.correlation_context(correlation_id):
        error_response = error_handler.handle_confluence_api_error(exc, correlation_id)
        status_code = exc.status_code or 500
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.dict(),
            headers={"X-Correlation-ID": correlation_id}
        )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    correlation_id = get_correlation_id(request)
    
    with logger.correlation_context(correlation_id):
        error_response = error_handler.handle_validation_error(exc, correlation_id)
        
        return JSONResponse(
            status_code=422,
            content=error_response.dict(),
            headers={"X-Correlation-ID": correlation_id}
        )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    correlation_id = get_correlation_id(request)
    
    with logger.correlation_context(correlation_id):
        error_response = error_handler.handle_generic_error(exc, correlation_id)
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict(),
            headers={"X-Correlation-ID": correlation_id}
        )

@app.post("/pages/extract", response_model=RunbookContent)
async def extract_page(
    request: PageExtractionRequest,
    confluence_client: ConfluenceClient = Depends(get_confluence_client),
    vector_store: VectorStore = Depends(get_vector_store)
) -> RunbookContent:
    """
    Extract runbook content from a single Confluence page.
    
    Retrieves page content, processes it for runbook information,
    and stores it in the vector database for semantic search.
    """
    try:
        # Get page content based on provided parameters
        if request.page_id:
            page_data = confluence_client.get_page_by_id(request.page_id)
        elif request.space_key and request.title:
            page_data = confluence_client.get_page_by_title(request.space_key, request.title)
        else:
            raise ValueError("Either page_id or both space_key and title must be provided")
        
        # Extract runbook content
        runbook_content = confluence_client.extract_runbook_content(page_data)
        
        # Store in vector database
        runbook_id = vector_store.add_runbook(runbook_content)
        
        # Add the generated runbook_id to the response (not in the model, but useful for tracking)
        return runbook_content
        
    except ConfluenceAPIError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=str(e))
        elif e.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication failed")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@app.post("/pages/bulk-extract", response_model=BulkExtractionResponse)
async def bulk_extract_pages(
    request: BulkExtractionRequest,
    background_tasks: BackgroundTasks,
    confluence_client: ConfluenceClient = Depends(get_confluence_client),
    vector_store: VectorStore = Depends(get_vector_store)
) -> BulkExtractionResponse:
    """
    Extract runbook content from multiple Confluence pages in parallel with job tracking.
    
    Creates a job for tracking progress and processes pages concurrently while handling
    individual failures without stopping the entire batch operation.
    
    Returns immediately with job ID for tracking progress via /jobs/{job_id} endpoint.
    """
    try:
        # Create job for tracking
        job_id = job_manager.create_job(request)
        
        # Start background task for processing
        background_tasks.add_task(
            job_manager.execute_bulk_extraction,
            job_id,
            request.page_ids,
            confluence_client,
            vector_store,
            request.concurrency_limit
        )
        
        # Return immediate response with job information
        return BulkExtractionResponse(
            job_id=job_id,
            status="pending",
            total_pages=len(request.page_ids),
            successful_extractions=0,
            failed_extractions=0,
            processing_time=None,
            errors=[]
        )
        
    except Exception as e:
        # If job creation fails, return error response
        return BulkExtractionResponse(
            job_id="",
            status="failed",
            total_pages=len(request.page_ids),
            successful_extractions=0,
            failed_extractions=len(request.page_ids),
            processing_time=0.0,
            errors=[f"Failed to create bulk extraction job: {str(e)}"]
        )


@app.get("/jobs/statistics")
async def get_job_statistics() -> Dict[str, Any]:
    """
    Get overall job statistics for monitoring and reporting.
    
    Returns:
        Dictionary containing comprehensive job statistics including:
        - Total jobs by status
        - Processing statistics
        - Performance metrics
    
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        stats = job_manager.get_job_statistics()
        
        # Add timestamp for when statistics were generated
        stats["generated_at"] = datetime.utcnow().isoformat()
        
        # Calculate success rate if there are processed pages
        total_extractions = stats["total_successful_extractions"] + stats["total_failed_extractions"]
        if total_extractions > 0:
            stats["success_rate"] = round(
                (stats["total_successful_extractions"] / total_extractions) * 100, 2
            )
        else:
            stats["success_rate"] = 0.0
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job statistics: {str(e)}")


@app.get("/jobs")
async def list_jobs(
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List all bulk extraction jobs with pagination.
    
    Args:
        limit: Maximum number of jobs to return (1-100, default: 20)
        offset: Number of jobs to skip for pagination (default: 0)
    
    Returns:
        Dictionary containing paginated job list and metadata
    
    Raises:
        HTTPException: 422 for invalid parameters
    """
    try:
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=422,
                detail="Limit must be between 1 and 100"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=422,
                detail="Offset must be non-negative"
            )
        
        # Get jobs from job manager
        jobs = job_manager.list_jobs(limit=limit, offset=offset)
        
        # Get total count for pagination metadata
        all_jobs = job_manager.list_jobs(limit=1000, offset=0)
        total_count = len(all_jobs)
        
        # Calculate pagination metadata
        has_next = (offset + limit) < total_count
        has_previous = offset > 0
        
        return {
            "jobs": [job.dict() for job in jobs],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total_count": total_count,
                "returned_count": len(jobs),
                "has_next": has_next,
                "has_previous": has_previous,
                "next_offset": offset + limit if has_next else None,
                "previous_offset": max(0, offset - limit) if has_previous else None
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@app.get("/jobs/{job_id}", response_model=BulkExtractionJob)
async def get_job_status(job_id: str) -> BulkExtractionJob:
    """
    Get the status and details of a bulk extraction job.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        BulkExtractionJob containing complete job information
    
    Raises:
        HTTPException: 404 if job not found, 422 for invalid ID
    """
    try:
        # Validate job_id parameter
        if not job_id or not job_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Job ID cannot be empty"
            )
        
        # Get job from job manager
        job = job_manager.get_job(job_id.strip())
        
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{job_id}' not found"
            )
        
        return job
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job: {str(e)}")


@app.get("/jobs/{job_id}/summary")
async def get_job_summary(job_id: str) -> Dict[str, Any]:
    """
    Get detailed summary statistics for a specific bulk extraction job.
    
    Provides comprehensive analysis including processing times, error breakdown,
    success rates, and individual page results with performance metrics.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Dictionary containing detailed job summary with analytics
    
    Raises:
        HTTPException: 404 if job not found, 422 for invalid ID, 500 for server errors
    """
    try:
        # Validate job_id parameter
        if not job_id or not job_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Job ID cannot be empty"
            )
        
        # Get job summary from job manager
        summary = job_manager.get_job_summary(job_id.strip())
        
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{job_id}' not found"
            )
        
        return summary
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job summary: {str(e)}")


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running bulk extraction job.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Dictionary containing cancellation confirmation
    
    Raises:
        HTTPException: 404 if job not found, 422 for invalid ID, 409 if job cannot be cancelled
    """
    try:
        # Validate job_id parameter
        if not job_id or not job_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Job ID cannot be empty"
            )
        
        job_id = job_id.strip()
        
        # Get job from job manager
        job = job_manager.get_job(job_id)
        
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{job_id}' not found"
            )
        
        # Check if job can be cancelled
        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=409,
                detail=f"Job with status '{job.status}' cannot be cancelled"
            )
        
        # Update job status to cancelled
        job_manager.update_job_status(job_id, "cancelled")
        
        return {
            "message": f"Job '{job_id}' has been cancelled",
            "job_id": job_id,
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@app.post("/jobs/cleanup")
async def cleanup_old_jobs(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up old completed jobs to free memory.
    
    Args:
        max_age_hours: Maximum age in hours for completed jobs (default: 24)
    
    Returns:
        Dictionary containing cleanup results
    
    Raises:
        HTTPException: 422 for invalid parameters, 500 for server errors
    """
    try:
        # Validate max_age_hours parameter
        if max_age_hours < 1 or max_age_hours > 168:  # Max 1 week
            raise HTTPException(
                status_code=422,
                detail="max_age_hours must be between 1 and 168 (1 week)"
            )
        
        cleaned_count = job_manager.cleanup_old_jobs(max_age_hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} old jobs",
            "cleaned_jobs": cleaned_count,
            "max_age_hours": max_age_hours,
            "cleaned_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup jobs: {str(e)}")


@app.get("/search/confluence")
async def search_confluence_pages(
    query: str,
    space_key: Optional[str] = None,
    limit: int = 10,
    confluence_client: ConfluenceClient = Depends(get_confluence_client)
) -> Dict[str, Any]:
    """
    Search Confluence pages using text query with optional space filtering.
    
    Args:
        query: Search query string
        space_key: Optional space key to limit search scope
        limit: Maximum number of results to return (1-100, default: 10)
    
    Returns:
        Dictionary containing search results with page information
    """
    try:
        # Validate query parameter
        if not query or not query.strip():
            raise HTTPException(
                status_code=422,
                detail="Query parameter cannot be empty"
            )
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=422,
                detail="Limit must be between 1 and 100"
            )
        
        # Validate space_key if provided
        if space_key is not None and not space_key.strip():
            raise HTTPException(
                status_code=422,
                detail="Space key cannot be empty when provided"
            )
        
        start_time = datetime.utcnow()
        
        # Perform Confluence search
        search_results = confluence_client.search_pages(
            query=query.strip(),
            space_key=space_key.strip() if space_key else None,
            limit=limit
        )
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Format results
        formatted_results = []
        for page in search_results:
            formatted_results.append({
                "page_id": page.get("id", ""),
                "title": page.get("title", ""),
                "space_key": page.get("space", {}).get("key", ""),
                "space_name": page.get("space", {}).get("name", ""),
                "url": f"{confluence_client.base_url}/spaces/{page.get('space', {}).get('key', '')}/pages/{page.get('id', '')}",
                "last_modified": page.get("version", {}).get("when", ""),
                "author": page.get("version", {}).get("by", {}).get("displayName", "")
            })
        
        return {
            "results": formatted_results,
            "total_results": len(formatted_results),
            "query": query,
            "space_key": space_key,
            "limit": limit,
            "processing_time": processing_time
        }
        
    except ConfluenceAPIError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication failed")
        elif e.status_code == 403:
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search/runbooks", response_model=RunbookSearchResponse)
async def search_runbooks(
    query: str,
    limit: int = 5,
    vector_store: VectorStore = Depends(get_vector_store)
) -> RunbookSearchResponse:
    """
    Search stored runbooks using semantic similarity search.
    
    Args:
        query: Search query string for semantic matching
        limit: Maximum number of results to return (1-20, default: 5)
    
    Returns:
        RunbookSearchResponse containing semantically similar runbook chunks
    """
    try:
        # Validate query parameter
        if not query or not query.strip():
            raise HTTPException(
                status_code=422,
                detail="Query parameter cannot be empty"
            )
        
        # Validate limit parameter
        if limit < 1 or limit > 20:
            raise HTTPException(
                status_code=422,
                detail="Limit must be between 1 and 20"
            )
        
        start_time = datetime.utcnow()
        
        # Perform semantic search
        search_results = vector_store.search_runbooks(
            query=query.strip(),
            n_results=limit
        )
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        return RunbookSearchResponse(
            results=search_results,
            total_results=len(search_results),
            query=query,
            processing_time=processing_time
        )
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        # Vector store runtime errors (database issues, etc.)
        raise HTTPException(status_code=503, detail=f"Search service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/runbooks/{runbook_id}", response_model=RunbookContent)
async def get_runbook(
    runbook_id: str,
    vector_store: VectorStore = Depends(get_vector_store)
) -> RunbookContent:
    """
    Retrieve a specific runbook by its ID.
    
    Args:
        runbook_id: Unique runbook identifier
    
    Returns:
        RunbookContent object containing the complete runbook
    
    Raises:
        HTTPException: 404 if runbook not found, 422 for invalid ID, 500 for server errors
    """
    try:
        # Validate runbook_id parameter
        if not runbook_id or not runbook_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Runbook ID cannot be empty"
            )
        
        # Retrieve runbook from vector store
        runbook = vector_store.get_runbook_by_id(runbook_id.strip())
        
        if runbook is None:
            raise HTTPException(
                status_code=404,
                detail=f"Runbook with ID '{runbook_id}' not found"
            )
        
        return runbook
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runbook: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/runbooks/{runbook_id}", response_model=RunbookContent)
async def update_runbook(
    runbook_id: str,
    update_request: RunbookUpdateRequest,
    vector_store: VectorStore = Depends(get_vector_store)
) -> RunbookContent:
    """
    Update an existing runbook with new content and regenerate embeddings.
    
    Args:
        runbook_id: Unique runbook identifier
        update_request: Updated runbook content
    
    Returns:
        Updated RunbookContent object
    
    Raises:
        HTTPException: 404 if runbook not found, 422 for validation errors, 500 for server errors
    """
    try:
        # Validate runbook_id parameter
        if not runbook_id or not runbook_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Runbook ID cannot be empty"
            )
        
        runbook_id = runbook_id.strip()
        
        # Get existing runbook to merge with updates
        existing_runbook = vector_store.get_runbook_by_id(runbook_id)
        if existing_runbook is None:
            raise HTTPException(
                status_code=404,
                detail=f"Runbook with ID '{runbook_id}' not found"
            )
        
        # Create updated runbook content by merging existing with updates
        updated_runbook = RunbookContent(
            metadata=update_request.metadata or existing_runbook.metadata,
            procedures=update_request.procedures if update_request.procedures is not None else existing_runbook.procedures,
            troubleshooting_steps=update_request.troubleshooting_steps if update_request.troubleshooting_steps is not None else existing_runbook.troubleshooting_steps,
            prerequisites=update_request.prerequisites if update_request.prerequisites is not None else existing_runbook.prerequisites,
            raw_content=update_request.raw_content or existing_runbook.raw_content,
            structured_sections=update_request.structured_sections if update_request.structured_sections is not None else existing_runbook.structured_sections
        )
        
        # Update runbook in vector store
        vector_store.update_runbook(runbook_id, updated_runbook)
        
        # Return updated runbook
        return updated_runbook
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update runbook: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/runbooks/{runbook_id}")
async def delete_runbook(
    runbook_id: str,
    vector_store: VectorStore = Depends(get_vector_store)
) -> Dict[str, Any]:
    """
    Delete a runbook and all its associated chunks from the vector database.
    
    Args:
        runbook_id: Unique runbook identifier
    
    Returns:
        Dictionary containing deletion confirmation
    
    Raises:
        HTTPException: 404 if runbook not found, 422 for invalid ID, 500 for server errors
    """
    try:
        # Validate runbook_id parameter
        if not runbook_id or not runbook_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Runbook ID cannot be empty"
            )
        
        runbook_id = runbook_id.strip()
        
        # Check if runbook exists before deletion
        existing_runbook = vector_store.get_runbook_by_id(runbook_id)
        if existing_runbook is None:
            raise HTTPException(
                status_code=404,
                detail=f"Runbook with ID '{runbook_id}' not found"
            )
        
        # Delete runbook from vector store
        vector_store.delete_runbook(runbook_id)
        
        return {
            "message": f"Runbook '{runbook_id}' successfully deleted",
            "runbook_id": runbook_id,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete runbook: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/runbooks")
async def list_runbooks(
    limit: int = 20,
    offset: int = 0,
    vector_store: VectorStore = Depends(get_vector_store)
) -> Dict[str, Any]:
    """
    List all runbooks with pagination support.
    
    Args:
        limit: Maximum number of runbooks to return (1-100, default: 20)
        offset: Number of runbooks to skip for pagination (default: 0)
    
    Returns:
        Dictionary containing paginated runbook list and metadata
    
    Raises:
        HTTPException: 422 for invalid parameters, 500 for server errors
    """
    try:
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=422,
                detail="Limit must be between 1 and 100"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=422,
                detail="Offset must be non-negative"
            )
        
        # Get runbooks from vector store
        runbooks = vector_store.list_runbooks(limit=limit, offset=offset)
        
        # Get total count for pagination metadata (simplified approach)
        # In production, you'd want a more efficient count method
        all_runbooks = vector_store.list_runbooks(limit=1000, offset=0)
        total_count = len(all_runbooks)
        
        # Calculate pagination metadata
        has_next = (offset + limit) < total_count
        has_previous = offset > 0
        
        return {
            "runbooks": runbooks,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total_count": total_count,
                "returned_count": len(runbooks),
                "has_next": has_next,
                "has_previous": has_previous,
                "next_offset": offset + limit if has_next else None,
                "previous_offset": max(0, offset - limit) if has_previous else None
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runbooks: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint for monitoring service status.
    
    Checks connectivity to Confluence API and vector database,
    provides counts of stored data, and overall service status.
    
    Returns:
        HealthResponse containing detailed health information
    """
    confluence_connected = False
    vector_db_connected = False
    collections_count = 0
    total_runbooks = 0
    overall_status = "unhealthy"
    
    # Check Confluence connectivity
    try:
        client = ConfluenceClient()
        # Try a simple API call to test connectivity
        client.search_pages(query="test", limit=1)
        confluence_connected = True
    except Exception:
        # Confluence connection failed, but don't fail the health check
        confluence_connected = False
    
    # Check vector database connectivity
    try:
        store = VectorStore()
        # Test basic vector store operations
        stats = store.get_collection_stats()
        collections_count = 1 if stats.get("total_chunks", 0) >= 0 else 0
        total_runbooks = len(store.list_runbooks(limit=1000, offset=0))
        vector_db_connected = True
    except Exception:
        # Vector DB connection failed
        vector_db_connected = False
    
    # Determine overall status
    if confluence_connected and vector_db_connected:
        overall_status = "healthy"
    elif vector_db_connected:
        overall_status = "degraded"  # Can still serve searches without Confluence
    else:
        overall_status = "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        confluence_connected=confluence_connected,
        vector_db_connected=vector_db_connected,
        collections_count=collections_count,
        total_runbooks=total_runbooks,
        timestamp=datetime.utcnow()
    )


@app.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the service is ready to accept traffic,
    503 if not ready (dependencies unavailable).
    
    Returns:
        Dictionary with readiness status
    """
    try:
        # Check if vector store is available (minimum requirement)
        store = VectorStore()
        store.get_collection_stats()  # Simple operation to test connectivity
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Service is ready to accept requests"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Service not ready: {str(e)}"
            }
        )


@app.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the service is alive and functioning,
    500 if the service should be restarted.
    
    Returns:
        Dictionary with liveness status
    """
    try:
        # Basic application health check
        # Check if we can create basic objects and the app is responsive
        test_timestamp = datetime.utcnow()
        
        return {
            "status": "alive",
            "timestamp": test_timestamp.isoformat(),
            "message": "Service is alive and responsive",
            "uptime_check": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "dead",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Service liveness check failed: {str(e)}"
            }
        )


@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Prometheus-style metrics endpoint for monitoring.
    
    Provides operational metrics about the service including
    request counts, processing times, and resource usage.
    
    Returns:
        Dictionary containing various service metrics
    """
    try:
        # Get vector store metrics
        vector_store_metrics = {}
        try:
            store = VectorStore()
            stats = store.get_collection_stats()
            vector_store_metrics = {
                "collections_count": 1 if stats.get("total_chunks", 0) >= 0 else 0,
                "total_chunks": stats.get("total_chunks", 0),
                "total_runbooks": len(store.list_runbooks(limit=1000, offset=0)),
                "vector_db_status": "connected"
            }
        except Exception as e:
            vector_store_metrics = {
                "collections_count": 0,
                "total_chunks": 0,
                "total_runbooks": 0,
                "vector_db_status": f"error: {str(e)}"
            }
        
        # Get Confluence metrics
        confluence_metrics = {}
        try:
            client = ConfluenceClient()
            # Test connectivity with minimal API call
            client.search_pages(query="test", limit=1)
            confluence_metrics = {
                "confluence_status": "connected",
                "api_accessible": True
            }
        except Exception as e:
            confluence_metrics = {
                "confluence_status": f"error: {str(e)}",
                "api_accessible": False
            }
        
        # Thread pool metrics
        thread_pool_metrics = {
            "max_workers": thread_pool._max_workers,
            "active_threads": len([t for t in thread_pool._threads if t.is_alive()]) if hasattr(thread_pool, '_threads') else 0
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service_info": {
                "name": "confluence-integration-tool",
                "version": "0.1.0"
            },
            "vector_store": vector_store_metrics,
            "confluence": confluence_metrics,
            "thread_pool": thread_pool_metrics,
            "system": {
                "status": "operational"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect metrics: {str(e)}"
        )