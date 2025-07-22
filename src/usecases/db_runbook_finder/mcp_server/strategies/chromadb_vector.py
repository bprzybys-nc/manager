"""
ChromaDB Vector Storage Strategy Implementation.

This module provides the VectorStorageStrategy implementation that integrates
with the existing Confluence tool's VectorStore for semantic search operations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
import os
from datetime import datetime
import time

from .protocols import DBVectorStrategyABC
from ..exceptions import VectorSearchError, MCPRunbookError

logger = logging.getLogger(__name__)


class ChromaDBVectorStrategy(DBVectorStrategyABC):
    """
    ChromaDB-based vector storage strategy implementation.
    
    Integrates with the existing Confluence tool's VectorStore via HTTP API
    for semantic search and embedding operations. Implements VectorStorageStrategy
    protocol through structural subtyping.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize ChromaDB vector strategy.
        
        Args:
            base_url: Base URL for Confluence tool API (defaults to env var)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url or os.getenv("CONFLUENCE_TOOL_URL", "http://localhost:8000")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"ChromaDBVectorStrategy initialized with base_url: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Confluence tool API."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'RunbookRepositoryMCP/1.0'
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """
        Check if ChromaDB vector store is accessible and healthy.
        
        Returns:
            True if vector store is healthy
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("vector_db_connected", False)
            return False
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
    
    # VectorStorageStrategy Protocol Implementation
    async def store_runbook_embedding(self, runbook_id: str, content: str, 
                                    metadata: Dict[str, Any]) -> bool:
        """
        Store runbook with vector embedding using Confluence tool's vector store.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Text content to embed
            metadata: Associated metadata
            
        Returns:
            True if storage successful
        """
        try:
            client = await self._get_client()
            
            # Use the existing Confluence tool's runbook extraction endpoint
            # which automatically stores embeddings in ChromaDB
            payload = {
                "page_id": runbook_id,
                "content": content,
                "metadata": metadata
            }
            
            # The /pages/extract endpoint processes content and stores in vector DB
            response = await client.post(f"{self.base_url}/pages/extract", json=payload)
            
            if response.status_code == 200:
                logger.info(f"Successfully stored runbook embedding: {runbook_id}")
                return True
            elif response.status_code == 422:
                logger.error(f"Validation error storing runbook {runbook_id}: {response.text}")
                return False
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to store runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to store runbook embedding: {e}")
        
        return False
    
    async def search_similar_runbooks(self, query: str, limit: int = 5, 
                                    min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform semantic search for similar runbooks with performance optimization.
        
        Args:
            query: Search query for similarity matching
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of similar runbooks with similarity scores
        """
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            # Use existing vector search endpoint with optimized parameters
            params = {
                "query": query,
                "limit": min(limit, 20)  # Respect API limits
            }
            
            response = await client.get(f"{self.base_url}/search/runbooks", params=params)
            
            if response.status_code == 200:
                search_data = response.json()
                results = search_data.get("results", [])
                processing_time = search_data.get("processing_time", 0.0)
                
                # Filter by minimum score if specified
                if min_score > 0.0:
                    results = [r for r in results if r.get("similarity_score", 0.0) >= min_score]
                
                # Ensure performance requirement (<50ms)
                total_time = time.time() - start_time
                if total_time > 0.05:  # 50ms
                    logger.warning(f"Vector search exceeded 50ms target: {total_time:.3f}s")
                
                logger.info(f"Vector search completed in {total_time:.3f}s, found {len(results)} results")
                
                # Transform results to standardized format
                standardized_results = []
                for result in results:
                    standardized_result = self._standardize_search_result(result, query)
                    standardized_results.append(standardized_result)
                
                return standardized_results[:limit]
                
            elif response.status_code == 422:
                raise VectorSearchError(query, "Invalid search query parameters")
            else:
                response.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                raise VectorSearchError(query, "Vector search service unavailable")
            raise VectorSearchError(query, f"HTTP error: {e}")
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Vector search failed after {total_time:.3f}s: {e}")
            raise VectorSearchError(query, str(e))
        
        return []
    
    async def update_runbook_embedding(self, runbook_id: str, content: str, 
                                     metadata: Dict[str, Any]) -> bool:
        """
        Update existing runbook embedding in ChromaDB.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Updated text content
            metadata: Updated metadata
            
        Returns:
            True if update successful
        """
        try:
            client = await self._get_client()
            
            # Use the existing update endpoint
            payload = {
                "content": content,
                "metadata": metadata
            }
            
            response = await client.put(f"{self.base_url}/runbooks/{runbook_id}", json=payload)
            
            if response.status_code == 200:
                logger.info(f"Successfully updated runbook embedding: {runbook_id}")
                return True
            elif response.status_code == 404:
                logger.warning(f"Runbook not found for update: {runbook_id}")
                # Try storing as new runbook instead
                return await self.store_runbook_embedding(runbook_id, content, metadata)
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to update runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to update runbook embedding: {e}")
        
        return False
    
    async def delete_runbook_embedding(self, runbook_id: str) -> bool:
        """
        Delete runbook from ChromaDB vector store.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            True if deletion successful
        """
        try:
            client = await self._get_client()
            
            response = await client.delete(f"{self.base_url}/runbooks/{runbook_id}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted runbook embedding: {runbook_id}")
                return True
            elif response.status_code == 404:
                logger.warning(f"Runbook not found for deletion: {runbook_id}")
                return True  # Consider not found as successful deletion
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to delete runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to delete runbook embedding: {e}")
        
        return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get ChromaDB collection statistics and health metrics.
        
        Returns:
            Statistics dictionary with collection info
        """
        try:
            client = await self._get_client()
            
            # Get metrics from the existing Confluence tool
            response = await client.get(f"{self.base_url}/metrics")
            
            if response.status_code == 200:
                metrics_data = response.json()
                vector_store_metrics = metrics_data.get("vector_store", {})
                
                # Standardize the statistics format
                stats = {
                    "total_runbooks": vector_store_metrics.get("total_runbooks", 0),
                    "total_chunks": vector_store_metrics.get("total_chunks", 0),
                    "collections_count": vector_store_metrics.get("collections_count", 0),
                    "vector_dimensions": 384,  # all-MiniLM-L6-v2 model dimension
                    "embedding_model": "all-MiniLM-L6-v2",
                    "database_status": vector_store_metrics.get("vector_db_status", "unknown"),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                return stats
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise MCPRunbookError(f"Failed to get collection statistics: {e}")
    
    async def list_stored_runbooks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all stored runbooks with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of stored runbook metadata
        """
        try:
            client = await self._get_client()
            
            params = {
                "limit": min(limit, 100),  # Respect API limits
                "offset": offset
            }
            
            response = await client.get(f"{self.base_url}/runbooks", params=params)
            
            if response.status_code == 200:
                data = response.json()
                runbooks = data.get("runbooks", [])
                
                # Standardize the response format
                standardized_runbooks = []
                for runbook in runbooks:
                    if isinstance(runbook, dict):
                        standardized_runbook = {
                            "runbook_id": runbook.get("id", ""),
                            "title": runbook.get("title", ""),
                            "metadata": runbook.get("metadata", {}),
                            "created_at": runbook.get("created_at", ""),
                            "updated_at": runbook.get("updated_at", ""),
                            "chunk_count": runbook.get("chunk_count", 1)
                        }
                        standardized_runbooks.append(standardized_runbook)
                
                return standardized_runbooks
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to list stored runbooks: {e}")
            raise MCPRunbookError(f"Failed to list stored runbooks: {e}")
    
    # Helper Methods
    def _standardize_search_result(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Standardize search result format for consistency.
        
        Args:
            result: Raw search result from Confluence tool
            query: Original search query
            
        Returns:
            Standardized search result dictionary
        """
        return {
            "runbook_id": result.get("runbook_id", result.get("id", "")),
            "title": result.get("title", ""),
            "content_preview": result.get("content", "")[:200] + "..." if result.get("content") else "",
            "similarity_score": result.get("similarity_score", result.get("score", 0.0)),
            "metadata": result.get("metadata", {}),
            "source": "chromadb",
            "search_query": query,
            "chunk_id": result.get("chunk_id", ""),
            "distance": result.get("distance", None),
            "matched_at": datetime.utcnow().isoformat()
        }
    
    def _validate_performance(self, start_time: float, operation: str) -> None:
        """
        Validate operation performance against requirements.
        
        Args:
            start_time: Operation start time
            operation: Operation name for logging
        """
        elapsed = time.time() - start_time
        if elapsed > 0.05:  # 50ms requirement
            logger.warning(f"{operation} exceeded 50ms performance target: {elapsed:.3f}s")
        else:
            logger.debug(f"{operation} completed within performance target: {elapsed:.3f}s")