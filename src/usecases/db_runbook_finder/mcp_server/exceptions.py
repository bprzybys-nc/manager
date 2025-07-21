"""
Custom exception hierarchy for RunbookRepositoryMCP Server.

This module defines the exception hierarchy for MCP server operations,
extending the base GraphMCP framework exceptions.
"""

from src.frameworks.graphmcp.clients.base import MCPToolError, MCPConnectionError


class MCPRunbookError(MCPToolError):
    """Base exception for runbook operations."""
    pass


class RunbookNotFoundError(MCPRunbookError):
    """Runbook not found in any strategy implementation."""
    
    def __init__(self, runbook_id: str, message: str = None):
        self.runbook_id = runbook_id
        if message is None:
            message = f"Runbook with ID '{runbook_id}' not found in any available strategy"
        super().__init__(message)


class VectorSearchError(MCPRunbookError):
    """Vector search operation failed."""
    
    def __init__(self, query: str, message: str = None):
        self.query = query
        if message is None:
            message = f"Vector search failed for query: '{query}'"
        super().__init__(message)


class StrategyUnavailableError(MCPRunbookError):
    """Strategy implementation unavailable, attempting fallback."""
    
    def __init__(self, strategy_name: str, reason: str = None):
        self.strategy_name = strategy_name
        if reason:
            message = f"Strategy '{strategy_name}' unavailable: {reason}"
        else:
            message = f"Strategy '{strategy_name}' unavailable"
        super().__init__(message)


class RunbookValidationError(MCPRunbookError):
    """Runbook content validation failed."""
    
    def __init__(self, runbook_id: str, validation_errors: list):
        self.runbook_id = runbook_id
        self.validation_errors = validation_errors
        message = f"Runbook '{runbook_id}' validation failed: {', '.join(validation_errors)}"
        super().__init__(message)


class NotificationError(MCPRunbookError):
    """Notification delivery failed."""
    
    def __init__(self, channel: str, message: str = None):
        self.channel = channel
        if message is None:
            message = f"Failed to send notification to channel '{channel}'"
        super().__init__(message)


class IncidentTrackingError(MCPRunbookError):
    """Incident tracking or data persistence failed."""
    
    def __init__(self, incident_id: str, operation: str, reason: str = None):
        self.incident_id = incident_id
        self.operation = operation
        if reason:
            message = f"Incident tracking failed for '{incident_id}' during {operation}: {reason}"
        else:
            message = f"Incident tracking failed for '{incident_id}' during {operation}"
        super().__init__(message)