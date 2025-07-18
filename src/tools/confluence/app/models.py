"""
Data models for the Confluence Integration Tool.

This module contains Pydantic models for data validation and serialization
used throughout the Confluence integration service.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator, HttpUrl


class RunbookMetadata(BaseModel):
    """Metadata for a runbook extracted from Confluence."""
    
    title: str = Field(..., min_length=1, max_length=500, description="Title of the runbook")
    author: Optional[str] = Field(None, max_length=100, description="Author of the runbook")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    space_key: str = Field(..., min_length=1, max_length=50, description="Confluence space key")
    page_id: str = Field(..., min_length=1, max_length=50, description="Confluence page ID")
    page_url: HttpUrl = Field(..., description="URL to the Confluence page")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the runbook")
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags list."""
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        for tag in v:
            if not isinstance(tag, str) or len(tag.strip()) == 0:
                raise ValueError('Tags must be non-empty strings')
            if len(tag) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
        return [tag.strip() for tag in v]


class RunbookContent(BaseModel):
    """Complete runbook content with structured sections."""
    
    metadata: RunbookMetadata = Field(..., description="Runbook metadata")
    procedures: List[str] = Field(default_factory=list, description="List of procedures")
    troubleshooting_steps: List[str] = Field(default_factory=list, description="Troubleshooting steps")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    raw_content: str = Field(..., description="Raw extracted content")
    structured_sections: Dict[str, str] = Field(default_factory=dict, description="Structured content sections")
    
    @validator('procedures', 'troubleshooting_steps', 'prerequisites')
    def validate_content_lists(cls, v):
        """Validate content lists."""
        if len(v) > 100:
            raise ValueError('Maximum 100 items allowed per list')
        for item in v:
            if not isinstance(item, str) or len(item.strip()) == 0:
                raise ValueError('List items must be non-empty strings')
            if len(item) > 5000:
                raise ValueError('Item length cannot exceed 5000 characters')
        return [item.strip() for item in v]
    
    @validator('raw_content')
    def validate_raw_content(cls, v):
        """Validate raw content."""
        if len(v.strip()) == 0:
            raise ValueError('Raw content cannot be empty')
        if len(v) > 1000000:  # 1MB limit
            raise ValueError('Raw content cannot exceed 1MB')
        return v.strip()


class RunbookChunk(BaseModel):
    """Individual chunk of runbook content for vector storage."""
    
    chunk_id: str = Field(..., min_length=1, max_length=100, description="Unique chunk identifier")
    runbook_id: str = Field(..., min_length=1, max_length=100, description="Parent runbook identifier")
    content: str = Field(..., min_length=1, max_length=1000, description="Chunk content")
    section_type: str = Field(..., min_length=1, max_length=50, description="Type of section")
    metadata: RunbookMetadata = Field(..., description="Associated runbook metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for the chunk")
    
    @validator('embedding')
    def validate_embedding(cls, v):
        """Validate embedding vector."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('Embedding must be a list of floats')
            if len(v) == 0:
                raise ValueError('Embedding cannot be empty')
            if len(v) > 1000:
                raise ValueError('Embedding dimension cannot exceed 1000')
            for val in v:
                if not isinstance(val, (int, float)):
                    raise ValueError('Embedding values must be numeric')
        return v


class PageExtractionRequest(BaseModel):
    """Request model for single page extraction."""
    
    page_id: Optional[str] = Field(None, min_length=1, max_length=50, description="Confluence page ID")
    space_key: Optional[str] = Field(None, min_length=1, max_length=50, description="Confluence space key")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Page title")
    
    @validator('page_id', 'space_key', 'title', pre=True)
    def strip_strings(cls, v):
        """Strip whitespace from string fields."""
        return v.strip() if isinstance(v, str) else v
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate that at least one identification method is provided
        if not self.page_id and not (self.space_key and self.title):
            raise ValueError('Either page_id or both space_key and title must be provided')


class BulkExtractionRequest(BaseModel):
    """Request model for bulk page extraction."""
    
    page_ids: List[str] = Field(..., min_items=1, max_items=100, description="List of Confluence page IDs")
    space_key: Optional[str] = Field(None, min_length=1, max_length=50, description="Optional space key filter")
    concurrency_limit: int = Field(default=5, ge=1, le=20, description="Maximum concurrent extractions")
    
    @validator('page_ids')
    def validate_page_ids(cls, v):
        """Validate page IDs list."""
        if not v:
            raise ValueError('At least one page ID must be provided')
        
        cleaned_ids = []
        for page_id in v:
            if not isinstance(page_id, str):
                raise ValueError('Page IDs must be strings')
            cleaned_id = page_id.strip()
            if len(cleaned_id) == 0:
                raise ValueError('Page IDs cannot be empty')
            if len(cleaned_id) > 50:
                raise ValueError('Page ID length cannot exceed 50 characters')
            cleaned_ids.append(cleaned_id)
        
        # Check for duplicates
        if len(set(cleaned_ids)) != len(cleaned_ids):
            raise ValueError('Duplicate page IDs are not allowed')
        
        return cleaned_ids


class SearchResult(BaseModel):
    """Search result for runbook queries."""
    
    runbook_id: str = Field(..., min_length=1, description="Runbook identifier")
    chunk_id: str = Field(..., min_length=1, description="Chunk identifier")
    content: str = Field(..., min_length=1, description="Matching content")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    metadata: RunbookMetadata = Field(..., description="Runbook metadata")


class RunbookSearchResponse(BaseModel):
    """Response model for runbook search operations."""
    
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    query: str = Field(..., min_length=1, description="Original search query")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    
    # Note: Results count validation removed due to Pydantic V2 compatibility issues


class ConfluenceSearchRequest(BaseModel):
    """Request model for Confluence page search."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    space_key: Optional[str] = Field(None, min_length=1, max_length=50, description="Optional space key filter")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    
    @validator('query', pre=True)
    def strip_query(cls, v):
        """Strip whitespace from query."""
        if isinstance(v, str):
            stripped = v.strip()
            if len(stripped) == 0:
                raise ValueError('Query cannot be empty')
            return stripped
        return v


class RunbookSearchRequest(BaseModel):
    """Request model for semantic runbook search."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of results")
    
    @validator('query', pre=True)
    def strip_query(cls, v):
        """Strip whitespace from query."""
        if isinstance(v, str):
            stripped = v.strip()
            if len(stripped) == 0:
                raise ValueError('Query cannot be empty')
            return stripped
        return v


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Overall service status")
    confluence_connected: bool = Field(..., description="Confluence API connectivity status")
    vector_db_connected: bool = Field(..., description="Vector database connectivity status")
    collections_count: int = Field(..., ge=0, description="Number of vector database collections")
    total_runbooks: int = Field(..., ge=0, description="Total number of stored runbooks")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")


class JobStatus:
    """Job status constants for bulk operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageExtractionResult(BaseModel):
    """Result for individual page extraction in bulk operations."""
    
    page_id: str = Field(..., description="Confluence page ID")
    runbook_id: Optional[str] = Field(None, description="Generated runbook ID if successful")
    title: Optional[str] = Field(None, description="Page title if extracted")
    success: bool = Field(..., description="Whether extraction was successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time: float = Field(..., ge=0, description="Processing time for this page")


class BulkExtractionJob(BaseModel):
    """Complete job information for bulk extraction operations."""
    
    job_id: str = Field(..., min_length=1, description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    total_pages: int = Field(..., ge=0, description="Total pages to process")
    processed_pages: int = Field(default=0, ge=0, description="Number of pages processed")
    successful_extractions: int = Field(default=0, ge=0, description="Number of successful extractions")
    failed_extractions: int = Field(default=0, ge=0, description="Number of failed extractions")
    processing_time: Optional[float] = Field(None, ge=0, description="Total processing time in seconds")
    page_results: List[PageExtractionResult] = Field(default_factory=list, description="Individual page results")
    errors: List[str] = Field(default_factory=list, description="General error messages")
    concurrency_limit: int = Field(default=5, ge=1, le=20, description="Concurrency limit for this job")


class BulkExtractionResponse(BaseModel):
    """Response model for bulk extraction operations."""
    
    job_id: str = Field(..., min_length=1, description="Job identifier")
    status: str = Field(..., description="Current job status")
    total_pages: int = Field(..., ge=0, description="Total pages to process")
    successful_extractions: int = Field(..., ge=0, description="Number of successful extractions")
    failed_extractions: int = Field(..., ge=0, description="Number of failed extractions")
    processing_time: Optional[float] = Field(None, ge=0, description="Total processing time in seconds")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    
    # Note: Extraction count validation removed due to Pydantic V2 compatibility issues


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    error: str = Field(..., min_length=1, description="Error type or category")
    detail: str = Field(..., min_length=1, description="Detailed error message")
    error_code: str = Field(..., min_length=1, description="Specific error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    
    @validator('error_code')
    def validate_error_code(cls, v):
        """Validate error code format."""
        if not v.isupper():
            raise ValueError('Error code must be uppercase')
        if len(v) > 20:
            raise ValueError('Error code cannot exceed 20 characters')
        return v


class RunbookUpdateRequest(BaseModel):
    """Request model for updating runbook content."""
    
    metadata: Optional[RunbookMetadata] = Field(None, description="Updated metadata")
    procedures: Optional[List[str]] = Field(None, description="Updated procedures")
    troubleshooting_steps: Optional[List[str]] = Field(None, description="Updated troubleshooting steps")
    prerequisites: Optional[List[str]] = Field(None, description="Updated prerequisites")
    raw_content: Optional[str] = Field(None, description="Updated raw content")
    structured_sections: Optional[Dict[str, str]] = Field(None, description="Updated structured sections")
    
    @validator('procedures', 'troubleshooting_steps', 'prerequisites')
    def validate_optional_lists(cls, v):
        """Validate optional content lists."""
        if v is not None:
            if len(v) > 100:
                raise ValueError('Maximum 100 items allowed per list')
            for item in v:
                if not isinstance(item, str) or len(item.strip()) == 0:
                    raise ValueError('List items must be non-empty strings')
                if len(item) > 5000:
                    raise ValueError('Item length cannot exceed 5000 characters')
            return [item.strip() for item in v]
        return v
    
    @validator('raw_content')
    def validate_optional_raw_content(cls, v):
        """Validate optional raw content."""
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError('Raw content cannot be empty')
            if len(v) > 1000000:  # 1MB limit
                raise ValueError('Raw content cannot exceed 1MB')
            return v.strip()
        return v