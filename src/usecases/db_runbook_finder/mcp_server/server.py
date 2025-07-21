"""
RunbookRepositoryMCP Server Implementation.

This module provides the main MCP server implementation with tool registration,
health checks, and strategy orchestration for the quadruple strategy pattern.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid
import time

from .strategies.protocols import (
    RunbookDiscoveryStrategy,
    VectorStorageStrategy, 
    DataPersistenceStrategy,
    NotificationStrategy
)
from .exceptions import (
    MCPRunbookError,
    RunbookNotFoundError,
    VectorSearchError,
    StrategyUnavailableError,
    RunbookValidationError,
    NotificationError,
    IncidentTrackingError
)

logger = logging.getLogger(__name__)


class RunbookRepositoryMCPServer:
    """
    Main MCP server implementation for runbook repository operations.
    
    Orchestrates the quadruple strategy pattern with discovery, vector storage,
    data persistence, and notification strategies.
    """
    
    def __init__(self, 
                 discovery_strategy: RunbookDiscoveryStrategy,
                 vector_strategy: VectorStorageStrategy,
                 persistence_strategy: DataPersistenceStrategy,
                 notification_strategy: NotificationStrategy):
        """
        Initialize MCP server with strategy implementations.
        
        Args:
            discovery_strategy: Runbook discovery implementation
            vector_strategy: Vector storage implementation
            persistence_strategy: Data persistence implementation
            notification_strategy: Notification implementation
        """
        self.discovery_strategy = discovery_strategy
        self.vector_strategy = vector_strategy
        self.persistence_strategy = persistence_strategy
        self.notification_strategy = notification_strategy
        
        # Tool registry
        self._tools: Dict[str, Callable] = {}
        self._register_tools()
        
        # Server metadata
        self.server_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        
        logger.info(f"RunbookRepositoryMCPServer initialized with ID: {self.server_id}")
    
    def _register_tools(self) -> None:
        """Register all available MCP tools."""
        # Discovery tools
        self._tools["discover_runbooks"] = self.discover_runbooks
        self._tools["get_runbook_content"] = self.get_runbook_content
        self._tools["search_runbooks_by_query"] = self.search_runbooks_by_query
        self._tools["validate_runbook_content"] = self.validate_runbook_content
        
        # Vector storage tools
        self._tools["store_runbook_embedding"] = self.store_runbook_embedding
        self._tools["search_similar_runbooks"] = self.search_similar_runbooks
        self._tools["update_runbook_embedding"] = self.update_runbook_embedding
        self._tools["delete_runbook_embedding"] = self.delete_runbook_embedding
        self._tools["get_vector_stats"] = self.get_vector_stats
        
        # Data persistence tools
        self._tools["track_runbook_usage"] = self.track_runbook_usage
        self._tools["get_runbook_metrics"] = self.get_runbook_metrics
        self._tools["create_incident_ticket"] = self.create_incident_ticket
        self._tools["update_ticket_status"] = self.update_ticket_status
        self._tools["get_incident_history"] = self.get_incident_history
        
        # Notification tools
        self._tools["send_runbook_notification"] = self.send_runbook_notification
        self._tools["create_approval_thread"] = self.create_approval_thread
        self._tools["update_thread_status"] = self.update_thread_status
        self._tools["send_completion_summary"] = self.send_completion_summary
        
        # Server management tools
        self._tools["health_check"] = self.health_check
        self._tools["get_server_info"] = self.get_server_info
        self._tools["list_tools"] = self.list_tools
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP tool call with error handling and logging.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPRunbookError: If tool execution fails
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Tool call started: {tool_name} (request_id: {request_id})")
        
        try:
            if tool_name not in self._tools:
                raise MCPRunbookError(f"Unknown tool: {tool_name}")
            
            # Execute tool
            tool_func = self._tools[tool_name]
            result = await tool_func(**arguments)
            
            execution_time = time.time() - start_time
            logger.info(f"Tool call completed: {tool_name} in {execution_time:.3f}s (request_id: {request_id})")
            
            # Add metadata to result
            if isinstance(result, dict):
                result.update({
                    "execution_time": execution_time,
                    "request_id": request_id,
                    "server_id": self.server_id
                })
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool call failed: {tool_name} after {execution_time:.3f}s - {e} (request_id: {request_id})")
            raise MCPRunbookError(f"Tool '{tool_name}' failed: {e}")
    
    # Discovery Tool Implementations
    async def discover_runbooks(self, spaces: List[str], limit: int = 10) -> Dict[str, Any]:
        """Discover runbooks in specified spaces."""
        try:
            runbooks = await self.discovery_strategy.discover_runbooks(spaces)
            return {
                "success": True,
                "runbooks": runbooks[:limit],
                "total_found": len(runbooks),
                "spaces_searched": spaces
            }
        except Exception as e:
            raise StrategyUnavailableError("discovery", str(e))
    
    async def get_runbook_content(self, runbook_id: str) -> Dict[str, Any]:
        """Get specific runbook content."""
        try:
            content = await self.discovery_strategy.get_runbook_content(runbook_id)
            if content is None:
                return {"found": False, "runbook_id": runbook_id}
            
            return {
                "found": True,
                "content": content,
                "runbook_id": runbook_id
            }
        except Exception as e:
            raise RunbookNotFoundError(runbook_id, str(e))
    
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, 
                                     limit: int = 10) -> Dict[str, Any]:
        """Search runbooks by text query."""
        try:
            results = await self.discovery_strategy.search_runbooks_by_query(query, spaces, limit)
            return {
                "success": True,
                "results": results,
                "query": query,
                "total_results": len(results)
            }
        except Exception as e:
            raise MCPRunbookError(f"Runbook search failed: {e}")
    
    async def validate_runbook_content(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Validate runbook content structure."""
        try:
            is_valid = await self.discovery_strategy.validate_runbook_content(page)
            metadata = {}
            
            if is_valid:
                metadata = await self.discovery_strategy.extract_runbook_metadata(page)
            
            return {
                "valid": is_valid,
                "metadata": metadata,
                "validation_timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise RunbookValidationError("unknown", [str(e)])
    
    # Vector Storage Tool Implementations
    async def store_runbook_embedding(self, runbook_id: str, content: str, 
                                    metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store runbook with vector embedding."""
        try:
            success = await self.vector_strategy.store_runbook_embedding(runbook_id, content, metadata)
            return {
                "success": success,
                "runbook_id": runbook_id,
                "stored_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise MCPRunbookError(f"Failed to store runbook embedding: {e}")
    
    async def search_similar_runbooks(self, query: str, limit: int = 5, 
                                    min_score: float = 0.0) -> Dict[str, Any]:
        """Perform semantic search for similar runbooks."""
        try:
            results = await self.vector_strategy.search_similar_runbooks(query, limit, min_score)
            return {
                "success": True,
                "results": results,
                "query": query,
                "total_results": len(results),
                "min_score": min_score
            }
        except Exception as e:
            raise VectorSearchError(query, str(e))
    
    async def update_runbook_embedding(self, runbook_id: str, content: str, 
                                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing runbook embedding."""
        try:
            success = await self.vector_strategy.update_runbook_embedding(runbook_id, content, metadata)
            return {
                "success": success,
                "runbook_id": runbook_id,
                "updated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise MCPRunbookError(f"Failed to update runbook embedding: {e}")
    
    async def delete_runbook_embedding(self, runbook_id: str) -> Dict[str, Any]:
        """Delete runbook from vector store."""
        try:
            success = await self.vector_strategy.delete_runbook_embedding(runbook_id)
            return {
                "success": success,
                "runbook_id": runbook_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise MCPRunbookError(f"Failed to delete runbook embedding: {e}")
    
    async def get_vector_stats(self) -> Dict[str, Any]:
        """Get vector store collection statistics."""
        try:
            stats = await self.vector_strategy.get_collection_stats()
            return {
                "success": True,
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise MCPRunbookError(f"Failed to get vector stats: {e}")
    
    # Data Persistence Tool Implementations
    async def track_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> Dict[str, Any]:
        """Track runbook usage for effectiveness metrics."""
        try:
            usage_id = await self.persistence_strategy.save_runbook_usage(runbook_id, usage_context)
            return {
                "success": True,
                "usage_id": usage_id,
                "runbook_id": runbook_id,
                "tracked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise IncidentTrackingError(usage_context.get("incident_id", "unknown"), "usage_tracking", str(e))
    
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """Get runbook effectiveness metrics."""
        try:
            metrics = await self.persistence_strategy.get_runbook_metrics(runbook_id)
            return {
                "success": True,
                "runbook_id": runbook_id,
                "metrics": metrics,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise MCPRunbookError(f"Failed to get runbook metrics: {e}")
    
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create incident ticket linked to runbook usage."""
        try:
            ticket_id = await self.persistence_strategy.create_incident_ticket(runbook_id, context)
            return {
                "success": True,
                "ticket_id": ticket_id,
                "runbook_id": runbook_id,
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise IncidentTrackingError(context.get("incident_id", "unknown"), "ticket_creation", str(e))
    
    async def update_ticket_status(self, ticket_id: str, status: str, 
                                 comment: Optional[str] = None) -> Dict[str, Any]:
        """Update incident ticket status."""
        try:
            success = await self.persistence_strategy.update_ticket_status(ticket_id, status, comment)
            return {
                "success": success,
                "ticket_id": ticket_id,
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise IncidentTrackingError(ticket_id, "status_update", str(e))
    
    async def get_incident_history(self, incident_id: str) -> Dict[str, Any]:
        """Get incident history including runbook usage."""
        try:
            history = await self.persistence_strategy.get_incident_history(incident_id)
            return {
                "success": True,
                "incident_id": incident_id,
                "history": history,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise IncidentTrackingError(incident_id, "history_retrieval", str(e))
    
    # Notification Tool Implementations
    async def send_runbook_notification(self, channel: str, runbook_id: str, 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Send runbook discovery notification."""
        try:
            notification_id = await self.notification_strategy.send_runbook_notification(channel, runbook_id, context)
            return {
                "success": True,
                "notification_id": notification_id,
                "channel": channel,
                "runbook_id": runbook_id,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise NotificationError(channel, f"Failed to send runbook notification: {e}")
    
    async def create_approval_thread(self, channel: str, runbook_id: str, 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Create approval thread for runbook execution."""
        try:
            thread_id = await self.notification_strategy.create_approval_thread(channel, runbook_id, context)
            return {
                "success": True,
                "thread_id": thread_id,
                "channel": channel,
                "runbook_id": runbook_id,
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise NotificationError(channel, f"Failed to create approval thread: {e}")
    
    async def update_thread_status(self, thread_id: str, status: str, 
                                 results: Dict[str, Any]) -> Dict[str, Any]:
        """Update thread with execution status."""
        try:
            success = await self.notification_strategy.update_thread_status(thread_id, status, results)
            return {
                "success": success,
                "thread_id": thread_id,
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise NotificationError("unknown", f"Failed to update thread status: {e}")
    
    async def send_completion_summary(self, channel: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Send workflow completion summary."""
        try:
            message_id = await self.notification_strategy.send_completion_summary(channel, summary)
            return {
                "success": True,
                "message_id": message_id,
                "channel": channel,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise NotificationError(channel, f"Failed to send completion summary: {e}")
    
    # Server Management Tool Implementations
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "healthy": True,
            "server_id": self.server_id,
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat(),
            "strategies": {}
        }
        
        # Check each strategy
        strategies = [
            ("discovery", self.discovery_strategy),
            ("vector", self.vector_strategy),
            ("persistence", self.persistence_strategy),
            ("notification", self.notification_strategy)
        ]
        
        for name, strategy in strategies:
            try:
                # Try to call a basic method if available
                if hasattr(strategy, 'health_check'):
                    strategy_health = await strategy.health_check()
                else:
                    # Assume healthy if no health check method
                    strategy_health = True
                    
                health_status["strategies"][name] = {
                    "healthy": strategy_health,
                    "type": type(strategy).__name__
                }
                
                if not strategy_health:
                    health_status["healthy"] = False
                    
            except Exception as e:
                health_status["strategies"][name] = {
                    "healthy": False,
                    "error": str(e),
                    "type": type(strategy).__name__
                }
                health_status["healthy"] = False
        
        return health_status
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information and statistics."""
        return {
            "server_id": self.server_id,
            "start_time": self.start_time.isoformat(),
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "available_tools": list(self._tools.keys()),
            "tool_count": len(self._tools),
            "strategies": {
                "discovery": type(self.discovery_strategy).__name__,
                "vector": type(self.vector_strategy).__name__,
                "persistence": type(self.persistence_strategy).__name__,
                "notification": type(self.notification_strategy).__name__
            }
        }
    
    async def list_tools(self) -> Dict[str, Any]:
        """List all available tools with descriptions."""
        tool_descriptions = {
            # Discovery tools
            "discover_runbooks": "Discover runbooks in specified spaces",
            "get_runbook_content": "Get specific runbook content by ID",
            "search_runbooks_by_query": "Search runbooks by text query",
            "validate_runbook_content": "Validate runbook content structure",
            
            # Vector storage tools
            "store_runbook_embedding": "Store runbook with vector embedding",
            "search_similar_runbooks": "Perform semantic search for similar runbooks", 
            "update_runbook_embedding": "Update existing runbook embedding",
            "delete_runbook_embedding": "Delete runbook from vector store",
            "get_vector_stats": "Get vector store statistics",
            
            # Data persistence tools
            "track_runbook_usage": "Track runbook usage for metrics",
            "get_runbook_metrics": "Get runbook effectiveness metrics",
            "create_incident_ticket": "Create incident ticket",
            "update_ticket_status": "Update incident ticket status",
            "get_incident_history": "Get incident history",
            
            # Notification tools
            "send_runbook_notification": "Send runbook discovery notification",
            "create_approval_thread": "Create approval thread",
            "update_thread_status": "Update thread status", 
            "send_completion_summary": "Send workflow completion summary",
            
            # Server management
            "health_check": "Perform server health check",
            "get_server_info": "Get server information", 
            "list_tools": "List all available tools"
        }
        
        return {
            "tools": [
                {"name": name, "description": tool_descriptions.get(name, "No description")}
                for name in self._tools.keys()
            ],
            "total_count": len(self._tools)
        }