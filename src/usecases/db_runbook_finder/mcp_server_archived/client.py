"""
RunbookRepositoryMCP Client Implementation.

This module provides the MCP client for the RunbookRepositoryMCP server,
following GraphMCP BaseClient patterns with full compliance.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.frameworks.graphmcp.clients.base import BaseMCPClient, MCPToolError
from .exceptions import (
    MCPRunbookError, 
    RunbookNotFoundError, 
    VectorSearchError
)

logger = logging.getLogger(__name__)


class RunbookRepositoryMCPClient(BaseMCPClient):
    """
    MCP client for runbook repository operations.
    
    Provides access to runbook discovery, vector search, data persistence,
    and notification operations through a unified MCP interface.
    """
    
    SERVER_NAME = "runbook_repository"  # Required class attribute
    
    def __init__(self, config_path: str | Path):
        """
        Initialize RunbookRepositoryMCP client.
        
        Args:
            config_path: Path to MCP configuration file
        """
        super().__init__(config_path)
        logger.info(f"Initialized RunbookRepositoryMCPClient for server '{self.SERVER_NAME}'")
    
    async def list_available_tools(self) -> List[str]:
        """
        List available tools for this MCP server.
        
        Returns:
            List of available tool names
        """
        try:
            response = await self._send_mcp_request("tools/list", {})
            return response.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list available tools: {e}")
            return [
                # Default tools that should be available
                "discover_runbooks",
                "get_runbook_content",
                "search_similar_runbooks",
                "store_runbook_embedding", 
                "create_incident_ticket",
                "send_runbook_notification",
                "track_runbook_usage"
            ]
    
    async def health_check(self) -> bool:
        """
        Perform health check on the MCP server.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self.call_tool_with_retry("health_check", {})
            return response.get("healthy", False)
        except Exception as e:
            logger.warning(f"Health check failed for {self.SERVER_NAME}: {e}")
            return False
    
    # Runbook Discovery Operations
    async def discover_runbooks(self, spaces: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover runbooks in specified spaces.
        
        Args:
            spaces: List of space keys to search
            limit: Maximum number of runbooks to return
            
        Returns:
            List of discovered runbook metadata
            
        Raises:
            MCPRunbookError: If discovery operation fails
        """
        try:
            params = {"spaces": spaces, "limit": limit}
            response = await self.call_tool_with_retry("discover_runbooks", params)
            return response.get("runbooks", [])
        except MCPToolError as e:
            raise MCPRunbookError(f"Runbook discovery failed: {e}")
    
    async def get_runbook_content(self, runbook_id: str) -> Dict[str, Any]:
        """
        Get specific runbook content.
        
        Args:
            runbook_id: Unique runbook identifier
            
        Returns:
            Runbook content dictionary
            
        Raises:
            RunbookNotFoundError: If runbook not found
        """
        try:
            params = {"runbook_id": runbook_id}
            response = await self.call_tool_with_retry("get_runbook_content", params)
            
            if not response.get("found", False):
                raise RunbookNotFoundError(runbook_id)
                
            return response.get("content", {})
        except MCPToolError as e:
            if "not found" in str(e).lower():
                raise RunbookNotFoundError(runbook_id)
            raise MCPRunbookError(f"Failed to get runbook content: {e}")
    
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, 
                                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search runbooks by text query.
        
        Args:
            query: Search query string
            spaces: Optional list of spaces to search
            limit: Maximum results to return
            
        Returns:
            List of matching runbook results
        """
        try:
            params = {"query": query, "limit": limit}
            if spaces:
                params["spaces"] = spaces
                
            response = await self.call_tool_with_retry("search_runbooks_by_query", params)
            return response.get("results", [])
        except MCPToolError as e:
            raise MCPRunbookError(f"Runbook search failed: {e}")
    
    # Vector Search Operations  
    async def search_similar_runbooks(self, query: str, limit: int = 5, 
                                    min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform semantic search for similar runbooks.
        
        Args:
            query: Search query for similarity matching
            limit: Maximum results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of similar runbooks with scores
            
        Raises:
            VectorSearchError: If search operation fails
        """
        try:
            params = {"query": query, "limit": limit, "min_score": min_score}
            response = await self.call_tool_with_retry("search_similar_runbooks", params)
            return response.get("results", [])
        except MCPToolError as e:
            raise VectorSearchError(query, str(e))
    
    async def store_runbook_embedding(self, runbook_id: str, content: str, 
                                    metadata: Dict[str, Any]) -> bool:
        """
        Store runbook with vector embedding.
        
        Args:
            runbook_id: Unique runbook identifier
            content: Text content to embed
            metadata: Associated metadata
            
        Returns:
            True if storage successful
        """
        try:
            params = {"runbook_id": runbook_id, "content": content, "metadata": metadata}
            response = await self.call_tool_with_retry("store_runbook_embedding", params)
            return response.get("success", False)
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to store runbook embedding: {e}")
    
    # Data Persistence Operations
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Create incident ticket linked to runbook usage.
        
        Args:
            runbook_id: Associated runbook
            context: Incident details and context
            
        Returns:
            Created ticket ID
        """
        try:
            params = {"runbook_id": runbook_id, "context": context}
            response = await self.call_tool_with_retry("create_incident_ticket", params)
            return response.get("ticket_id", "")
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to create incident ticket: {e}")
    
    async def track_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """
        Track runbook usage for effectiveness metrics.
        
        Args:
            runbook_id: Runbook being tracked
            usage_context: Usage details and context
            
        Returns:
            Usage record ID
        """
        try:
            params = {"runbook_id": runbook_id, "usage_context": usage_context}
            response = await self.call_tool_with_retry("track_runbook_usage", params)
            return response.get("usage_id", "")
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to track runbook usage: {e}")
    
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """
        Get runbook effectiveness metrics.
        
        Args:
            runbook_id: Runbook to get metrics for
            
        Returns:
            Metrics dictionary with usage stats
        """
        try:
            params = {"runbook_id": runbook_id}
            response = await self.call_tool_with_retry("get_runbook_metrics", params)
            return response.get("metrics", {})
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to get runbook metrics: {e}")
    
    # Notification Operations
    async def send_runbook_notification(self, channel: str, runbook_id: str, 
                                      context: Dict[str, Any]) -> str:
        """
        Send runbook discovery notification.
        
        Args:
            channel: Communication channel
            runbook_id: Associated runbook
            context: Notification context
            
        Returns:
            Notification/thread ID
        """
        try:
            params = {"channel": channel, "runbook_id": runbook_id, "context": context}
            response = await self.call_tool_with_retry("send_runbook_notification", params)
            return response.get("notification_id", "")
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to send runbook notification: {e}")
    
    async def create_approval_thread(self, channel: str, runbook_id: str, 
                                   context: Dict[str, Any]) -> str:
        """
        Create approval thread for runbook execution.
        
        Args:
            channel: Communication channel
            runbook_id: Runbook requiring approval
            context: Approval context
            
        Returns:
            Thread ID
        """
        try:
            params = {"channel": channel, "runbook_id": runbook_id, "context": context}
            response = await self.call_tool_with_retry("create_approval_thread", params)
            return response.get("thread_id", "")
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to create approval thread: {e}")
    
    async def update_thread_status(self, thread_id: str, status: str, 
                                 results: Dict[str, Any]) -> bool:
        """
        Update thread with execution status.
        
        Args:
            thread_id: Thread to update
            status: Current status
            results: Execution results
            
        Returns:
            True if update successful
        """
        try:
            params = {"thread_id": thread_id, "status": status, "results": results}
            response = await self.call_tool_with_retry("update_thread_status", params)
            return response.get("success", False)
        except MCPToolError as e:
            raise MCPRunbookError(f"Failed to update thread status: {e}")
    
    # Convenience Methods
    async def comprehensive_runbook_search(self, query: str, spaces: Optional[List[str]] = None,
                                         include_semantic: bool = True, limit: int = 5) -> Dict[str, Any]:
        """
        Perform comprehensive runbook search combining text and semantic search.
        
        Args:
            query: Search query
            spaces: Optional spaces to search
            include_semantic: Whether to include semantic search results
            limit: Maximum results per search type
            
        Returns:
            Combined search results with metadata
        """
        results = {
            "query": query,
            "text_results": [],
            "semantic_results": [],
            "combined_count": 0
        }
        
        # Text search
        try:
            text_results = await self.search_runbooks_by_query(query, spaces, limit)
            results["text_results"] = text_results
        except Exception as e:
            logger.warning(f"Text search failed: {e}")
        
        # Semantic search
        if include_semantic:
            try:
                semantic_results = await self.search_similar_runbooks(query, limit)
                results["semantic_results"] = semantic_results
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")
        
        results["combined_count"] = len(results["text_results"]) + len(results["semantic_results"])
        return results