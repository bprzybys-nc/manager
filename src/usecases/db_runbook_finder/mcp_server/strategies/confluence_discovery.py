"""
Confluence Runbook Discovery Strategy Implementation.

This module provides the RunbookDiscoveryStrategy implementation that integrates
with the existing Confluence tool for runbook discovery operations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
import os
from datetime import datetime

from .protocols import AbstractDiscoveryStrategy
from ..exceptions import MCPRunbookError, RunbookNotFoundError

logger = logging.getLogger(__name__)


class ConfluenceRunbookStrategy(AbstractDiscoveryStrategy):
    """
    Confluence-based runbook discovery strategy implementation.
    
    Integrates with the existing Confluence tool via HTTP API to discover,
    retrieve, and validate runbook content. Implements RunbookDiscoveryStrategy
    protocol through structural subtyping.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize Confluence strategy.
        
        Args:
            base_url: Base URL for Confluence tool API (defaults to env var)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url or os.getenv("CONFLUENCE_TOOL_URL", "http://localhost:8000")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"ConfluenceRunbookStrategy initialized with base_url: {self.base_url}")
    
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
        Check if Confluence tool is accessible and healthy.
        
        Returns:
            True if Confluence tool is healthy
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Confluence health check failed: {e}")
            return False
    
    # RunbookDiscoveryStrategy Protocol Implementation
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        """
        Discover runbooks in specified Confluence spaces.
        
        Args:
            spaces: List of Confluence space keys to search
            
        Returns:
            List of runbook metadata dictionaries
        """
        try:
            client = await self._get_client()
            all_runbooks = []
            
            for space in spaces:
                try:
                    # Search for runbooks in this space using Confluence tool API
                    params = {
                        "query": "runbook OR procedure OR troubleshooting",
                        "space_key": space,
                        "limit": 50
                    }
                    
                    response = await client.get(f"{self.base_url}/search/confluence", params=params)
                    
                    if response.status_code == 200:
                        search_results = response.json()
                        
                        # Filter and transform results to runbook metadata
                        for result in search_results.get("results", []):
                            if self._is_likely_runbook(result):
                                runbook_metadata = await self._transform_to_runbook_metadata(result)
                                all_runbooks.append(runbook_metadata)
                    
                    elif response.status_code == 404:
                        logger.warning(f"Space '{space}' not found or not accessible")
                    else:
                        logger.error(f"Failed to search space '{space}': {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error searching space '{space}': {e}")
                    continue
            
            logger.info(f"Discovered {len(all_runbooks)} runbooks across {len(spaces)} spaces")
            return all_runbooks
            
        except Exception as e:
            raise MCPRunbookError(f"Failed to discover runbooks: {e}")
    
    async def get_runbook_content(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific runbook content from Confluence.
        
        Args:
            runbook_id: Confluence page ID
            
        Returns:
            Runbook content dictionary or None if not found
        """
        try:
            client = await self._get_client()
            
            # Get runbook content from vector store (which has processed content)
            response = await client.get(f"{self.base_url}/runbooks/{runbook_id}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise MCPRunbookError(f"Failed to get runbook content: {e}")
        except Exception as e:
            raise MCPRunbookError(f"Failed to get runbook content: {e}")
    
    async def validate_runbook_content(self, page: Dict[str, Any]) -> bool:
        """
        Validate if page content represents a valid runbook.
        
        Args:
            page: Page content dictionary
            
        Returns:
            True if content appears to be a valid runbook
        """
        try:
            # Check for required runbook elements
            title = page.get("title", "").lower()
            content = page.get("content", "").lower()
            
            # Runbook indicators
            runbook_indicators = [
                "runbook", "procedure", "troubleshooting", "step-by-step",
                "how to", "guide", "instructions", "process", "workflow"
            ]
            
            # Check title for runbook indicators
            title_has_indicators = any(indicator in title for indicator in runbook_indicators)
            
            # Check content structure
            has_steps = any(step_word in content for step_word in ["step", "1.", "2.", "first", "then", "next"])
            has_sections = len(content) > 500  # Runbooks typically have substantial content
            
            # Must have either strong title indicators or content structure
            is_valid = title_has_indicators or (has_steps and has_sections)
            
            logger.debug(f"Runbook validation: title_indicators={title_has_indicators}, "
                        f"has_steps={has_steps}, has_sections={has_sections}, valid={is_valid}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating runbook content: {e}")
            return False
    
    async def extract_runbook_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from runbook page.
        
        Args:
            page: Page content dictionary
            
        Returns:
            Metadata dictionary with standardized fields
        """
        try:
            metadata = {
                "title": page.get("title", ""),
                "page_id": page.get("page_id", page.get("id", "")),
                "space_key": page.get("space_key", ""),
                "space_name": page.get("space_name", ""),
                "url": page.get("url", ""),
                "last_modified": page.get("last_modified", ""),
                "author": page.get("author", ""),
                "tags": page.get("tags", []),
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            # Extract additional metadata from content if available
            content = page.get("content", "")
            if content:
                metadata.update(self._extract_content_metadata(content))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting runbook metadata: {e}")
            return {"error": str(e), "extracted_at": datetime.utcnow().isoformat()}
    
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, 
                                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search runbooks by text query using Confluence search.
        
        Args:
            query: Search query string
            spaces: Optional list of spaces to search (searches all if None)
            limit: Maximum results to return
            
        Returns:
            List of matching runbook dictionaries
        """
        try:
            client = await self._get_client()
            
            # Enhanced query for runbook-specific search
            enhanced_query = f"({query}) AND (runbook OR procedure OR troubleshooting OR guide)"
            
            params = {
                "query": enhanced_query,
                "limit": limit
            }
            
            # Add space filter if specified
            if spaces:
                # For multiple spaces, we'll search each individually and combine
                all_results = []
                for space in spaces:
                    space_params = params.copy()
                    space_params["space_key"] = space
                    
                    response = await client.get(f"{self.base_url}/search/confluence", params=space_params)
                    if response.status_code == 200:
                        results = response.json().get("results", [])
                        all_results.extend(results)
                
                # Sort by relevance and limit
                all_results = all_results[:limit]
            else:
                response = await client.get(f"{self.base_url}/search/confluence", params=params)
                if response.status_code == 200:
                    all_results = response.json().get("results", [])
                else:
                    response.raise_for_status()
            
            # Transform results to standardized format
            runbook_results = []
            for result in all_results:
                if self._is_likely_runbook(result):
                    transformed = await self._transform_to_runbook_metadata(result)
                    transformed["search_relevance"] = result.get("relevance", 0.0)
                    runbook_results.append(transformed)
            
            logger.info(f"Found {len(runbook_results)} runbooks for query: '{query}'")
            return runbook_results
            
        except Exception as e:
            raise MCPRunbookError(f"Runbook search failed: {e}")
    
    # Helper Methods
    def _is_likely_runbook(self, page: Dict[str, Any]) -> bool:
        """
        Check if a page is likely to be a runbook based on title and metadata.
        
        Args:
            page: Page dictionary from Confluence search
            
        Returns:
            True if page appears to be a runbook
        """
        title = page.get("title", "").lower()
        
        # Strong runbook indicators
        strong_indicators = ["runbook", "procedure", "troubleshooting", "playbook"]
        if any(indicator in title for indicator in strong_indicators):
            return True
        
        # Weaker indicators that need combination
        weak_indicators = ["guide", "how to", "instructions", "process", "workflow", "steps"]
        weak_matches = sum(1 for indicator in weak_indicators if indicator in title)
        
        # Content-based hints if available
        content_hint = False
        if "content" in page or "body" in page:
            content_hint = True
        
        return weak_matches >= 2 or (weak_matches >= 1 and content_hint)
    
    async def _transform_to_runbook_metadata(self, confluence_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Confluence search result to standardized runbook metadata.
        
        Args:
            confluence_result: Raw result from Confluence search
            
        Returns:
            Standardized runbook metadata dictionary
        """
        return {
            "runbook_id": confluence_result.get("page_id", confluence_result.get("id", "")),
            "title": confluence_result.get("title", ""),
            "space_key": confluence_result.get("space_key", ""),
            "space_name": confluence_result.get("space_name", ""),
            "url": confluence_result.get("url", ""),
            "last_modified": confluence_result.get("last_modified", ""),
            "author": confluence_result.get("author", ""),
            "summary": confluence_result.get("excerpt", "")[:200] + "..." if confluence_result.get("excerpt") else "",
            "source": "confluence",
            "discovery_timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_content_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract additional metadata from runbook content.
        
        Args:
            content: Runbook text content
            
        Returns:
            Additional metadata dictionary
        """
        metadata = {}
        
        # Estimate complexity based on content length and structure
        content_lower = content.lower()
        
        # Count steps/procedures
        step_count = sum([
            content_lower.count("step "),
            content_lower.count("1."),
            content_lower.count("2."),
            content_lower.count("3."),
            len([line for line in content.split('\n') if line.strip().startswith(('1.', '2.', '3.'))])
        ])
        
        metadata["estimated_steps"] = max(step_count, content.count('\n') // 10)
        metadata["content_length"] = len(content)
        metadata["complexity"] = "high" if len(content) > 2000 else "medium" if len(content) > 500 else "low"
        
        # Identify categories based on content
        categories = []
        category_indicators = {
            "database": ["database", "db", "sql", "mysql", "postgresql", "mongodb"],
            "infrastructure": ["server", "network", "infrastructure", "deployment"],
            "security": ["security", "authentication", "authorization", "ssl", "certificate"],
            "monitoring": ["monitoring", "alert", "metric", "log", "performance"],
            "troubleshooting": ["troubleshoot", "debug", "error", "issue", "problem"]
        }
        
        for category, indicators in category_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                categories.append(category)
        
        metadata["categories"] = categories
        
        return metadata