"""
Database Decommissioning Use Case Module.

This module provides the database decommissioning workflow as a Manager use case,
integrating with Manager's FastAPI infrastructure while maintaining GraphMCP 
framework compatibility.

Following Manager architectural patterns:
- FastAPI integration for API endpoints
- Async-first design throughout
- Proper authentication and authorization
- Prometheus metrics integration
- Structured logging
- MongoDB integration for state management

Preserving GraphMCP integration:
- WorkflowBuilder pattern usage
- MCP client orchestration
- Workflow context management
- Structured logging system
"""

from .models import (
    FileProcessingResult,
    WorkflowConfig,
    QualityAssuranceResult,
    ValidationResult,
    DecommissioningSummary,
    WorkflowStepResult,
)

from .workflow_orchestrator import (
    DatabaseDecommissionOrchestrator,
    create_workflow,
    execute_workflow,
)

from .utils import (
    extract_repo_details,
    generate_workflow_id,
    validate_workflow_parameters,
    create_workflow_config,
    calculate_workflow_metrics,
    format_workflow_summary,
)

# Version and metadata
__version__ = "1.0.0"
__author__ = "Manager Database Decommissioning Team"

# Export main components
__all__ = [
    # Data models
    "FileProcessingResult",
    "WorkflowConfig",
    "QualityAssuranceResult",
    "ValidationResult",
    "DecommissioningSummary",
    "WorkflowStepResult",
    # Main orchestrator
    "DatabaseDecommissionOrchestrator",
    "create_workflow",
    "execute_workflow",
    # Utilities
    "extract_repo_details",
    "generate_workflow_id",
    "validate_workflow_parameters",
    "create_workflow_config",
    "calculate_workflow_metrics",
    "format_workflow_summary",
]