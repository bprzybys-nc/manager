"""
Base MCP Client Wrapper for Database Decommissioning.

This module provides the abstract base class for MCP client wrappers that integrate
GraphMCP framework clients with Manager-specific enhancements.

Manager Integration:
- Enhanced error handling with graceful degradation
- Manager-specific logging and metrics
- Tenant context and user management
- Configuration management integration

GraphMCP Preservation:
- Full compatibility with GraphMCP client patterns
- Async context manager support
- Standard MCP protocol compliance
"""

import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.clients.base import BaseMCPClient, MCPConnectionError, MCPToolError
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..utils import create_logger_for_workflow


class BaseMCPClientWrapper(ABC):
    """
    Abstract base class for MCP client wrappers with Manager integration.
    
    Provides standardized interface for MCP clients while preserving GraphMCP
    framework compatibility and adding Manager-specific enhancements.
    """

    def __init__(
        self,
        config_path: str | Path,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        retry_count: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize MCP client wrapper.

        Args:
            config_path: Path to MCP configuration file
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
            retry_count: Number of retry attempts for failed operations
            timeout: Timeout for MCP operations in seconds
        """
        self.config_path = Path(config_path)
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"mcp_client_{int(time.time())}"
        self.retry_count = retry_count
        self.timeout = timeout

        # Initialize logger
        self.logger = create_logger_for_workflow(
            self.workflow_id, "mcp_client", self.tenant_id
        )

        # Client will be initialized on first use
        self._client: Optional[BaseMCPClient] = None
        self._connection_healthy = False

    @property
    @abstractmethod
    def client_class(self) -> type:
        """Return the GraphMCP client class to instantiate."""
        pass

    @property
    @abstractmethod
    def server_name(self) -> str:
        """Return the MCP server name for this client."""
        pass

    async def _initialize_client(self) -> BaseMCPClient:
        """
        Initialize the underlying GraphMCP client.

        Returns:
            Initialized GraphMCP client instance
        """
        if self._client is None:
            try:
                self._client = self.client_class(self.config_path)
                self.logger.log_info(f"Initialized {self.server_name} MCP client")
            except Exception as e:
                self.logger.log_error(f"Failed to initialize {self.server_name} client", e)
                raise MCPConnectionError(f"Failed to initialize {self.server_name} client: {e}")

        return self._client

    async def health_check(self) -> bool:
        """
        Perform health check on the MCP client.

        Returns:
            True if client is healthy, False otherwise
        """
        try:
            client = await self._initialize_client()
            health_status = await client.health_check()
            self._connection_healthy = health_status
            
            if health_status:
                self.logger.log_info(f"{self.server_name} client health check passed")
            else:
                self.logger.log_warning(f"{self.server_name} client health check failed")
                
            return health_status

        except Exception as e:
            self.logger.log_error(f"{self.server_name} client health check error", e)
            self._connection_healthy = False
            return False

    async def is_available(self) -> bool:
        """
        Check if the MCP client is available for use.

        Returns:
            True if client is available, False otherwise
        """
        if not self._connection_healthy:
            return await self.health_check()
        return True

    async def call_tool_with_retry(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP tool with retry logic and enhanced error handling.

        Args:
            tool_name: Name of the MCP tool to call
            params: Parameters to pass to the tool

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool execution fails after all retries
        """
        client = await self._initialize_client()
        
        self.logger.log_info(
            f"Calling {self.server_name} tool: {tool_name}",
            {"tool_name": tool_name, "tenant_id": self.tenant_id}
        )

        try:
            result = await client.call_tool_with_retry(tool_name, params, self.retry_count)
            self.logger.log_info(f"{self.server_name} tool {tool_name} completed successfully")
            return result

        except MCPToolError as e:
            self.logger.log_error(f"{self.server_name} tool {tool_name} failed", e)
            # Mark connection as potentially unhealthy
            self._connection_healthy = False
            raise

        except Exception as e:
            self.logger.log_error(f"{self.server_name} tool {tool_name} unexpected error", e)
            # Mark connection as potentially unhealthy
            self._connection_healthy = False
            raise MCPToolError(f"Unexpected error calling {tool_name}: {e}")

    async def list_available_tools(self) -> list[str]:
        """
        List available tools for this MCP client.

        Returns:
            List of available tool names
        """
        try:
            client = await self._initialize_client()
            tools = await client.list_available_tools()
            self.logger.log_info(f"Listed {len(tools)} available tools for {self.server_name}")
            return tools

        except Exception as e:
            self.logger.log_error(f"Failed to list tools for {self.server_name}", e)
            return []

    async def close(self):
        """Close MCP client connection and cleanup resources."""
        if self._client:
            try:
                await self._client.close()
                self.logger.log_info(f"Closed {self.server_name} MCP client")
            except Exception as e:
                self.logger.log_warning(f"Error closing {self.server_name} client", e)
            finally:
                self._client = None
                self._connection_healthy = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

    def _create_enhanced_result(
        self, result: Dict[str, Any], operation: str, **metadata
    ) -> Dict[str, Any]:
        """
        Create enhanced result with Manager metadata.

        Args:
            result: Original result from MCP tool
            operation: Operation name for tracking
            **metadata: Additional metadata to include

        Returns:
            Enhanced result with Manager context
        """
        enhanced = {
            **result,
            "manager_metadata": {
                "tenant_id": self.tenant_id,
                "workflow_id": self.workflow_id,
                "operation": operation,
                "server_name": self.server_name,
                "timestamp": time.time(),
                **metadata,
            }
        }

        return enhanced

    def _handle_graceful_degradation(
        self, operation: str, error: Exception, fallback_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle graceful degradation when MCP operations fail.

        Args:
            operation: Operation that failed
            error: Exception that occurred
            fallback_result: Optional fallback result to return

        Returns:
            Graceful degradation result
        """
        self.logger.log_warning(
            f"Graceful degradation for {self.server_name} {operation}: {error}"
        )

        degraded_result = fallback_result or {
            "success": False,
            "degraded": True,
            "error": str(error),
            "operation": operation,
        }

        return self._create_enhanced_result(
            degraded_result, operation, degraded=True, error_type=type(error).__name__
        )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to MCP server with detailed reporting.

        Returns:
            Connection test results with diagnostics
        """
        start_time = time.time()
        
        try:
            # Test basic connection
            client = await self._initialize_client()
            
            # Test health check
            health_status = await self.health_check()
            
            # Test tool listing
            tools = await self.list_available_tools()
            
            duration = time.time() - start_time
            
            result = {
                "success": health_status,
                "server_name": self.server_name,
                "connection_time": duration,
                "tools_available": len(tools),
                "tools": tools,
                "config_path": str(self.config_path),
            }

            self.logger.log_info(
                f"{self.server_name} connection test completed",
                {"success": health_status, "duration": duration, "tools_count": len(tools)}
            )

            return self._create_enhanced_result(result, "connection_test")

        except Exception as e:
            duration = time.time() - start_time
            
            result = {
                "success": False,
                "server_name": self.server_name,
                "connection_time": duration,
                "error": str(e),
                "error_type": type(e).__name__,
                "config_path": str(self.config_path),
            }

            return self._create_enhanced_result(result, "connection_test", error=True)


# Legacy compatibility functions for GraphMCP integration
async def create_mcp_client_wrapper(
    client_type: str,
    config_path: str | Path,
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> BaseMCPClientWrapper:
    """
    Factory function to create MCP client wrappers.

    Args:
        client_type: Type of client ('github', 'slack', 'repomix')
        config_path: Path to MCP configuration file
        tenant_id: Optional tenant identifier
        workflow_id: Optional workflow identifier

    Returns:
        Initialized MCP client wrapper

    Raises:
        ValueError: If client_type is not supported
    """
    from .github_client import GitHubClientWrapper
    from .slack_client import SlackClientWrapper
    from .repomix_client import RepomixClientWrapper

    client_map = {
        "github": GitHubClientWrapper,
        "slack": SlackClientWrapper,
        "repomix": RepomixClientWrapper,
    }

    if client_type not in client_map:
        raise ValueError(f"Unsupported client type: {client_type}")

    client_class = client_map[client_type]
    return client_class(config_path, tenant_id, workflow_id)


async def test_all_clients(
    config_path: str | Path,
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Test all available MCP clients.

    Args:
        config_path: Path to MCP configuration file
        tenant_id: Optional tenant identifier
        workflow_id: Optional workflow identifier

    Returns:
        Test results for all clients
    """
    client_types = ["github", "slack", "repomix"]
    results = {}

    for client_type in client_types:
        try:
            wrapper = await create_mcp_client_wrapper(
                client_type, config_path, tenant_id, workflow_id
            )
            async with wrapper:
                results[client_type] = await wrapper.test_connection()
        except Exception as e:
            results[client_type] = {
                "success": False,
                "error": str(e),
                "client_type": client_type,
            }

    return results