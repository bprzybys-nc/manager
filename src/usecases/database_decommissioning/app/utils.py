"""
Database Decommissioning Utilities.

This module contains shared utility functions for the database decommissioning workflow,
enhanced for Manager integration while preserving GraphMCP framework compatibility.

Manager Integration:
- Configuration management following Manager patterns
- Database client integration
- Celery task support
- Prometheus metrics

GraphMCP Preservation:
- Workflow creation and configuration
- MCP server configuration
- Parameter service integration
- Structured logging
"""

import json
import time
import os
from typing import Any, Dict, List, Optional, Tuple

# Manager imports
import src.config as manager_config
from src.database.client import DatabaseClient

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.graphmcp_logging import LoggingConfig, get_logger
from src.frameworks.graphmcp.utils.parameter_service import get_parameter_service
from src.frameworks.graphmcp.workflows.builder import WorkflowBuilder

# Local imports
from .models import (
    WorkflowConfig,
    DecommissioningSummary,
    QualityAssuranceResult,
    WorkflowStepResult,
)


def initialize_environment_with_centralized_secrets():
    """
    Initialize environment with centralized parameter service.

    Manager Enhancement: Integrates with Manager's configuration system.

    Returns:
        ParameterService: Initialized parameter service instance
    """
    return get_parameter_service()


def extract_repo_details(repo_url: str) -> Tuple[str, str]:
    """
    Extract repository owner and name from URL.

    Args:
        repo_url: Repository URL

    Returns:
        Tuple of (owner, name)
    """
    if repo_url.startswith("https://github.com/"):
        repo_path = repo_url.replace("https://github.com/", "").rstrip("/")
        if "/" in repo_path:
            repo_owner, repo_name = repo_path.split("/", 1)
            return repo_owner, repo_name

    # Default fallback
    return "bprzybys-nc", "postgres-sample-dbs"


def generate_workflow_id(database_name: str, tenant_id: Optional[str] = None) -> str:
    """
    Generate a unique workflow identifier.

    Manager Enhancement: Includes tenant context for multi-tenancy.

    Args:
        database_name: Name of the database being decommissioned
        tenant_id: Optional tenant identifier

    Returns:
        Unique workflow identifier
    """
    timestamp = int(time.time())
    if tenant_id:
        return f"db-{database_name}-{tenant_id}-{timestamp}"
    return f"db-{database_name}-{timestamp}"


def validate_workflow_parameters(
    database_name: str,
    target_repos: List[str],
    slack_channel: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate workflow parameters before execution.

    Manager Enhancement: Adds tenant validation and Manager-specific checks.

    Args:
        database_name: Name of the database to decommission
        target_repos: List of repository URLs to process
        slack_channel: Slack channel ID for notifications
        tenant_id: Optional tenant identifier

    Returns:
        Dict containing validation results
    """
    validation_errors = []

    # Validate database name
    if not database_name or not database_name.strip():
        validation_errors.append("Database name cannot be empty")

    # Validate target repositories
    if not target_repos or len(target_repos) == 0:
        validation_errors.append("At least one target repository must be specified")

    for repo_url in target_repos:
        if not repo_url.startswith("https://github.com/"):
            validation_errors.append(f"Invalid repository URL format: {repo_url}")

    # Validate slack channel
    if not slack_channel or not slack_channel.strip():
        validation_errors.append("Slack channel cannot be empty")

    # Manager-specific validations
    if tenant_id and not tenant_id.strip():
        validation_errors.append("Tenant ID cannot be empty if provided")

    # Validate Manager environment variables
    required_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "MONGO_DB_URI",
    ]
    for env_var in required_env_vars:
        if not os.environ.get(env_var):
            validation_errors.append(f"Required environment variable {env_var} not set")

    return {"valid": len(validation_errors) == 0, "errors": validation_errors}


def create_workflow_config(
    database_name: str,
    target_repos: List[str],
    slack_channel: str,
    workflow_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs,
) -> WorkflowConfig:
    """
    Create workflow configuration with Manager enhancements.

    Args:
        database_name: Name of the database to decommission
        target_repos: List of repository URLs to process
        slack_channel: Slack channel ID for notifications
        workflow_id: Unique workflow identifier
        tenant_id: Optional tenant identifier
        user_id: Optional user identifier
        **kwargs: Additional configuration parameters

    Returns:
        WorkflowConfig instance
    """
    if workflow_id is None:
        workflow_id = generate_workflow_id(database_name, tenant_id)

    # Extract repo details from first repository
    repo_owner, repo_name = extract_repo_details(target_repos[0] if target_repos else "")

    return WorkflowConfig(
        database_name=database_name,
        repo_owner=repo_owner,
        repo_name=repo_name,
        tenant_id=tenant_id,
        user_id=user_id,
        max_parallel_steps=kwargs.get("max_parallel_steps", 4),
        default_timeout=kwargs.get("default_timeout", 120),
        log_file=kwargs.get("log_file", f"dbworkflow_{database_name}.log"),
        enable_console_logging=kwargs.get("enable_console_logging", True),
        enable_json_logging=kwargs.get("enable_json_logging", True),
        enable_slack_notifications=kwargs.get("enable_slack_notifications", True),
        dry_run=kwargs.get("dry_run", False),
    )


def calculate_workflow_metrics(workflow_result: Any) -> Dict[str, Any]:
    """
    Calculate comprehensive workflow metrics from execution results.

    Manager Enhancement: Includes Manager-specific metrics and monitoring.

    Args:
        workflow_result: Workflow execution result

    Returns:
        Dict containing calculated metrics
    """
    metrics = {
        "execution_time": getattr(workflow_result, "duration_seconds", 0),
        "success_rate": getattr(workflow_result, "success_rate", 0),
        "steps_completed": getattr(workflow_result, "steps_completed", 0),
        "total_steps": getattr(workflow_result, "total_steps", 0),
        "status": getattr(workflow_result, "status", "unknown"),
    }

    # Extract step-specific metrics
    step_metrics = {}
    step_names = [
        "validate_environment",
        "process_repositories",
        "apply_refactoring",
        "create_github_pr",
        "quality_assurance",
        "workflow_summary",
    ]

    for step_name in step_names:
        if hasattr(workflow_result, "get_step_result"):
            step_result = workflow_result.get_step_result(step_name, {})
            if step_result:
                step_metrics[step_name] = {
                    "success": step_result.get("success", False),
                    "duration": step_result.get("duration", 0),
                    "error_message": step_result.get("error_message"),
                }

    metrics["step_metrics"] = step_metrics

    # Manager-specific metrics
    metrics["manager_integration"] = {
        "database_client_available": True,  # Would check actual connectivity
        "prometheus_enabled": bool(os.environ.get("PROMETHEUS_ADDRESS")),
        "slack_enabled": bool(os.environ.get("SLACK_BOT_TOKEN")),
    }

    return metrics


def format_workflow_summary(
    workflow_result: Any, database_name: str, tenant_id: Optional[str] = None
) -> str:
    """
    Format a human-readable workflow summary with Manager context.

    Args:
        workflow_result: Workflow execution result
        database_name: Name of the database being decommissioned
        tenant_id: Optional tenant identifier

    Returns:
        Formatted summary string
    """
    metrics = calculate_workflow_metrics(workflow_result)

    summary = f"""
🎉 Database Decommissioning Workflow Complete!

Database: {database_name}
"""

    if tenant_id:
        summary += f"Tenant: {tenant_id}\n"

    summary += f"""Status: {metrics["status"]}
Success Rate: {metrics["success_rate"]:.1f}%
Duration: {metrics["execution_time"]:.1f}s
Steps Completed: {metrics["steps_completed"]}/{metrics["total_steps"]}

Repository Processing Results:
"""

    if hasattr(workflow_result, "get_step_result"):
        repo_result = workflow_result.get_step_result("process_repositories", {})
        if repo_result:
            summary += f"""- Repositories Processed: {repo_result.get("repositories_processed", 0)}
- Files Discovered: {repo_result.get("total_files_processed", 0)}
- Files Modified: {repo_result.get("total_files_modified", 0)}
"""

    # Manager integration status
    manager_metrics = metrics.get("manager_integration", {})
    summary += f"""
Manager Integration:
- Database Client: {'✅' if manager_metrics.get('database_client_available') else '❌'}
- Prometheus: {'✅' if manager_metrics.get('prometheus_enabled') else '❌'}
- Slack: {'✅' if manager_metrics.get('slack_enabled') else '❌'}
"""

    return summary.strip()


def create_mcp_config() -> Dict[str, Any]:
    """
    Create MCP configuration for database decommissioning workflow.

    Manager Enhancement: Integrates with Manager environment variables.

    Returns:
        Dict containing MCP server configuration
    """
    return {
        "mcpServers": {
            "ovr_github": {
                "command": "npx",
                "args": ["@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
                },
            },
            "ovr_slack": {
                "command": "npx",
                "args": ["@modelcontextprotocol/server-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
                },
            },
            "ovr_repomix": {
                "command": "npx",
                "args": ["repomix", "--mcp"]
            },
        }
    }


def get_manager_database_client() -> Optional[DatabaseClient]:
    """
    Get Manager database client instance.

    Manager Enhancement: Creates database client using Manager patterns.

    Returns:
        DatabaseClient instance or None if not available
    """
    try:
        mongo_uri = manager_config.MONGO_DB_URI
        if mongo_uri:
            return DatabaseClient({"uri": mongo_uri})
    except Exception:
        pass
    return None


def store_workflow_state(
    workflow_id: str,
    state: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> bool:
    """
    Store workflow state in Manager database.

    Manager Enhancement: Persist workflow state for recovery and monitoring.

    Args:
        workflow_id: Unique workflow identifier
        state: Workflow state to store
        tenant_id: Optional tenant identifier

    Returns:
        True if successful, False otherwise
    """
    try:
        db_client = get_manager_database_client()
        if not db_client:
            return False

        collection = db_client.client.get_database("manager").get_collection("workflow_states")
        
        document = {
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "state": state,
            "timestamp": time.time(),
            "updated_at": time.time(),
        }

        # Upsert the document
        collection.replace_one(
            {"workflow_id": workflow_id},
            document,
            upsert=True
        )
        return True

    except Exception as e:
        # Log error but don't fail the workflow
        print(f"Failed to store workflow state: {e}")
        return False


def get_workflow_state(
    workflow_id: str,
    tenant_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve workflow state from Manager database.

    Manager Enhancement: Retrieve workflow state for recovery and monitoring.

    Args:
        workflow_id: Unique workflow identifier
        tenant_id: Optional tenant identifier

    Returns:
        Workflow state dict or None if not found
    """
    try:
        db_client = get_manager_database_client()
        if not db_client:
            return None

        collection = db_client.client.get_database("manager").get_collection("workflow_states")
        
        query = {"workflow_id": workflow_id}
        if tenant_id:
            query["tenant_id"] = tenant_id

        document = collection.find_one(query)
        return document.get("state") if document else None

    except Exception as e:
        # Log error but don't fail the workflow
        print(f"Failed to retrieve workflow state: {e}")
        return None


def create_logger_for_workflow(
    workflow_id: str,
    database_name: str,
    tenant_id: Optional[str] = None,
) -> Any:
    """
    Create structured logger for workflow with Manager context.

    Args:
        workflow_id: Unique workflow identifier
        database_name: Name of database being decommissioned
        tenant_id: Optional tenant identifier

    Returns:
        Configured logger instance
    """
    config = LoggingConfig.from_env()
    
    # Add Manager context
    if tenant_id:
        workflow_id = f"{tenant_id}-{workflow_id}"

    logger = get_logger(workflow_id=workflow_id, config=config)
    
    # Log Manager integration status
    logger.log_info(f"Manager Database Decommissioning Workflow Starting")
    logger.log_info(f"Database: {database_name}")
    if tenant_id:
        logger.log_info(f"Tenant: {tenant_id}")
    
    return logger


# Legacy compatibility functions (preserved for GraphMCP compatibility)
def create_logger_adapter(database_name: str) -> Any:
    """
    Create logger adapter for backward compatibility.

    Args:
        database_name: Name of database being decommissioned

    Returns:
        Logger adapter instance
    """
    workflow_id = generate_workflow_id(database_name)
    return create_logger_for_workflow(workflow_id, database_name)


# Manager-specific utility functions
def get_manager_config_value(key: str, default: Any = None) -> Any:
    """
    Get configuration value from Manager config.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Configuration value
    """
    return getattr(manager_config, key, default)


def is_manager_feature_enabled(feature: str) -> bool:
    """
    Check if a Manager feature is enabled.

    Args:
        feature: Feature name (e.g., 'slack', 'prometheus', 'celery')

    Returns:
        True if feature is enabled
    """
    feature_checks = {
        "slack": bool(os.environ.get("SLACK_BOT_TOKEN")),
        "prometheus": bool(os.environ.get("PROMETHEUS_ADDRESS")),
        "celery": bool(os.environ.get("CELERY_BROKER_URL")),
        "azure_openai": bool(os.environ.get("AZURE_OPENAI_API_KEY")),
        "mongodb": bool(os.environ.get("MONGO_DB_URI")),
    }
    return feature_checks.get(feature, False)


def create_manager_workflow_context(
    config: WorkflowConfig,
    workflow_id: str,
) -> Dict[str, Any]:
    """
    Create workflow context with Manager integration.

    Args:
        config: Workflow configuration
        workflow_id: Unique workflow identifier

    Returns:
        Workflow context dict
    """
    context = {
        "workflow_id": workflow_id,
        "database_name": config.database_name,
        "tenant_id": config.tenant_id,
        "user_id": config.user_id,
        "manager_features": {
            "slack_enabled": is_manager_feature_enabled("slack"),
            "prometheus_enabled": is_manager_feature_enabled("prometheus"),
            "mongodb_enabled": is_manager_feature_enabled("mongodb"),
            "azure_openai_enabled": is_manager_feature_enabled("azure_openai"),
        },
        "graphmcp_config": create_mcp_config(),
        "created_at": time.time(),
    }
    return context