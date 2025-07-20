"""
Database Decommissioning API Module.

This module provides FastAPI routes and components for database decommissioning
workflows with Manager integration and GraphMCP framework compatibility.

Manager Integration:
- Standard Manager API patterns and route structure
- Tenant-aware workflow execution
- Database client integration for state persistence
- Celery task integration for background processing

GraphMCP Preservation:
- Full GraphMCP workflow orchestration compatibility
- Standard workflow configuration patterns
- MCP client integration and error handling
"""

from .routes import (
    DatabaseDecommissioningRoute,
    create_database_decommissioning_routes,
    get_database_decommissioning_router,
    WorkflowExecuteRequest,
)

__all__ = [
    "DatabaseDecommissioningRoute",
    "create_database_decommissioning_routes", 
    "get_database_decommissioning_router",
    "WorkflowExecuteRequest",
]