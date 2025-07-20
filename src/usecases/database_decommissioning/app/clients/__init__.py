"""
MCP Client Wrappers for Database Decommissioning.

This module provides Manager-integrated wrappers for GraphMCP framework MCP clients,
enabling standardized client interfaces for database decommissioning workflows.

Manager Integration:
- Enhanced error handling and retry logic
- Manager-specific logging and metrics
- Tenant context and user management
- Graceful degradation patterns

GraphMCP Preservation:
- Full GraphMCP client compatibility
- Standard MCP protocol support
- Async context manager patterns
"""

from .base import BaseMCPClientWrapper, create_mcp_client_wrapper, test_all_clients
from .github_client import GitHubClientWrapper
from .slack_client import SlackClientWrapper
from .repomix_client import RepomixClientWrapper

__all__ = [
    "BaseMCPClientWrapper",
    "GitHubClientWrapper",
    "SlackClientWrapper", 
    "RepomixClientWrapper",
    "create_mcp_client_wrapper",
    "test_all_clients",
]