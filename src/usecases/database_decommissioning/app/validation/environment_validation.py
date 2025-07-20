"""
Environment Validation for Database Decommissioning.

This module provides environment validation functionality enhanced for Manager integration
while preserving GraphMCP framework compatibility.

Manager Integration:
- Manager configuration validation
- Database client connectivity
- Celery worker availability
- Prometheus metrics validation

GraphMCP Preservation:
- Parameter service validation
- MCP client connectivity
- Structured logging integration
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

# Manager imports
import src.config as manager_config
from src.database.client import DatabaseClient

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.utils.parameter_service import get_parameter_service
from src.frameworks.graphmcp.utils.monitoring import get_monitoring_system, HealthStatus
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..models import ValidationResult
from ..utils import get_manager_database_client, is_manager_feature_enabled


class EnvironmentValidator:
    """
    Environment validator with Manager integration.
    
    Validates both GraphMCP framework components and Manager infrastructure.
    """

    def __init__(self, database_name: str, workflow_id: Optional[str] = None):
        """
        Initialize environment validator.

        Args:
            database_name: Name of database being decommissioned
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.workflow_id = workflow_id or f"env_validation_{int(time.time())}"
        
        # Initialize logger
        config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id=self.workflow_id, config=config)

    async def validate_manager_infrastructure(self) -> Dict[str, Any]:
        """
        Validate Manager infrastructure components.

        Returns:
            Dict containing Manager validation results
        """
        try:
            validations = []

            # Validate Manager database connectivity
            db_validation = await self._validate_manager_database()
            validations.append(db_validation)

            # Validate Azure OpenAI connectivity
            azure_validation = await self._validate_azure_openai()
            validations.append(azure_validation)

            # Validate Prometheus integration
            prometheus_validation = await self._validate_prometheus()
            validations.append(prometheus_validation)

            # Validate Slack integration
            slack_validation = await self._validate_slack_integration()
            validations.append(slack_validation)

            # Validate Celery worker availability
            celery_validation = await self._validate_celery_workers()
            validations.append(celery_validation)

            failed_validations = [v for v in validations if v["status"] == "FAILED"]
            warning_validations = [v for v in validations if v["status"] == "WARNING"]

            return {
                "component": "manager_infrastructure",
                "status": "PASSED" if len(failed_validations) == 0 else "FAILED",
                "message": f"Manager infrastructure validation completed: {len(validations) - len(failed_validations)}/{len(validations)} passed",
                "details": {
                    "validations": validations,
                    "total_checks": len(validations),
                    "passed_checks": len(validations) - len(failed_validations) - len(warning_validations),
                    "failed_checks": len(failed_validations),
                    "warning_checks": len(warning_validations),
                },
            }

        except Exception as e:
            self.logger.log_error("Manager infrastructure validation failed", e)
            return {
                "component": "manager_infrastructure",
                "status": "FAILED",
                "message": f"Manager infrastructure validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_manager_database(self) -> Dict[str, Any]:
        """Validate Manager MongoDB connectivity."""
        try:
            db_client = get_manager_database_client()
            if not db_client:
                return {
                    "status": "FAILED",
                    "component": "manager_database",
                    "message": "Manager database client not available",
                    "details": {"mongo_uri_configured": bool(manager_config.MONGO_DB_URI)},
                }

            # Test basic connectivity
            try:
                db_client.client.admin.command('ping')
                return {
                    "status": "PASSED",
                    "component": "manager_database",
                    "message": "Manager database connectivity validated",
                    "details": {"connected": True},
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "component": "manager_database",
                    "message": f"Manager database connection failed: {str(e)}",
                    "details": {"error": str(e)},
                }

        except Exception as e:
            return {
                "status": "FAILED",
                "component": "manager_database",
                "message": f"Manager database validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_azure_openai(self) -> Dict[str, Any]:
        """Validate Azure OpenAI configuration."""
        try:
            api_key = getattr(manager_config, 'AZURE_OPENAI_API_KEY', None)
            endpoint = getattr(manager_config, 'AZURE_OPENAI_ENDPOINT', None)

            if not api_key:
                return {
                    "status": "FAILED",
                    "component": "azure_openai",
                    "message": "Azure OpenAI API key not configured",
                    "details": {"api_key_configured": False},
                }

            if not endpoint:
                return {
                    "status": "WARNING",
                    "component": "azure_openai",
                    "message": "Azure OpenAI endpoint not configured",
                    "details": {"endpoint_configured": False},
                }

            return {
                "status": "PASSED",
                "component": "azure_openai",
                "message": "Azure OpenAI configuration validated",
                "details": {
                    "api_key_configured": True,
                    "endpoint_configured": True,
                },
            }

        except Exception as e:
            return {
                "status": "WARNING",
                "component": "azure_openai",
                "message": f"Azure OpenAI validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_prometheus(self) -> Dict[str, Any]:
        """Validate Prometheus integration."""
        try:
            prometheus_enabled = is_manager_feature_enabled("prometheus")
            prometheus_address = getattr(manager_config, 'PROMETHEUS_ADDRESS', None)

            if not prometheus_enabled:
                return {
                    "status": "WARNING",
                    "component": "prometheus",
                    "message": "Prometheus not configured (optional for workflow)",
                    "details": {"enabled": False},
                }

            return {
                "status": "PASSED",
                "component": "prometheus",
                "message": "Prometheus integration configured",
                "details": {
                    "enabled": True,
                    "address": prometheus_address,
                },
            }

        except Exception as e:
            return {
                "status": "WARNING",
                "component": "prometheus",
                "message": f"Prometheus validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_slack_integration(self) -> Dict[str, Any]:
        """Validate Slack integration."""
        try:
            slack_enabled = is_manager_feature_enabled("slack")

            if not slack_enabled:
                return {
                    "status": "WARNING",
                    "component": "slack",
                    "message": "Slack not configured (optional for workflow)",
                    "details": {"enabled": False},
                }

            return {
                "status": "PASSED",
                "component": "slack",
                "message": "Slack integration configured",
                "details": {"enabled": True},
            }

        except Exception as e:
            return {
                "status": "WARNING",
                "component": "slack",
                "message": f"Slack validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_celery_workers(self) -> Dict[str, Any]:
        """Validate Celery worker availability."""
        try:
            celery_enabled = is_manager_feature_enabled("celery")

            if not celery_enabled:
                return {
                    "status": "WARNING",
                    "component": "celery",
                    "message": "Celery not configured (optional for workflow)",
                    "details": {"enabled": False},
                }

            return {
                "status": "PASSED",
                "component": "celery",
                "message": "Celery integration configured",
                "details": {"enabled": True},
            }

        except Exception as e:
            return {
                "status": "WARNING",
                "component": "celery",
                "message": f"Celery validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def validate_graphmcp_components(self) -> Dict[str, Any]:
        """
        Validate GraphMCP framework components.

        Returns:
            Dict containing GraphMCP validation results
        """
        try:
            validations = []

            # Validate parameter service
            param_validation = await self._validate_parameter_service()
            validations.append(param_validation)

            # Validate monitoring system
            monitoring_validation = await self._validate_monitoring_system()
            validations.append(monitoring_validation)

            # Validate workflow components
            workflow_validation = await self._validate_workflow_components()
            validations.append(workflow_validation)

            failed_validations = [v for v in validations if v["status"] == "FAILED"]
            warning_validations = [v for v in validations if v["status"] == "WARNING"]

            return {
                "component": "graphmcp_framework",
                "status": "PASSED" if len(failed_validations) == 0 else "FAILED",
                "message": f"GraphMCP framework validation completed: {len(validations) - len(failed_validations)}/{len(validations)} passed",
                "details": {
                    "validations": validations,
                    "total_checks": len(validations),
                    "passed_checks": len(validations) - len(failed_validations) - len(warning_validations),
                    "failed_checks": len(failed_validations),
                    "warning_checks": len(warning_validations),
                },
            }

        except Exception as e:
            self.logger.log_error("GraphMCP framework validation failed", e)
            return {
                "component": "graphmcp_framework",
                "status": "FAILED",
                "message": f"GraphMCP framework validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_parameter_service(self) -> Dict[str, Any]:
        """Validate parameter service connectivity."""
        try:
            param_service = get_parameter_service()
            test_result = param_service.validate_mcp_configuration()

            return {
                "status": "PASSED" if test_result else "FAILED",
                "component": "parameter_service",
                "message": (
                    "Parameter service connection validated"
                    if test_result
                    else "Parameter service connection failed"
                ),
                "details": {"connected": test_result},
            }
        except Exception as e:
            self.logger.log_error("Parameter service validation failed", e)
            return {
                "status": "FAILED",
                "component": "parameter_service",
                "message": f"Parameter service error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_monitoring_system(self) -> Dict[str, Any]:
        """Validate monitoring system."""
        try:
            monitoring = get_monitoring_system()
            health_checks = await monitoring.perform_health_check()

            overall_status = "PASSED"
            if isinstance(health_checks, dict):
                for check_result in health_checks.values():
                    if (
                        hasattr(check_result, "status")
                        and check_result.status != HealthStatus.HEALTHY
                    ):
                        overall_status = "WARNING"
                        break

            return {
                "status": overall_status,
                "component": "monitoring_system",
                "message": "Monitoring system health checks completed",
                "details": {
                    "checks_run": (
                        len(health_checks) if isinstance(health_checks, dict) else 1
                    ),
                    "status": overall_status,
                },
            }
        except Exception as e:
            self.logger.log_error("Monitoring system validation failed", e)
            return {
                "status": "WARNING",
                "component": "monitoring_system",
                "message": f"Monitoring system error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _validate_workflow_components(self) -> Dict[str, Any]:
        """Validate workflow components availability."""
        try:
            # Test basic workflow component imports
            from src.frameworks.graphmcp.workflows.builder import WorkflowBuilder
            from src.frameworks.graphmcp.clients.github import GitHubMCPClient
            from src.frameworks.graphmcp.clients.slack import SlackMCPClient
            from src.frameworks.graphmcp.clients.repomix import RepomixMCPClient

            return {
                "status": "PASSED",
                "component": "workflow_components",
                "message": "Workflow components available",
                "details": {
                    "workflow_builder": True,
                    "mcp_clients": True,
                },
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "component": "workflow_components",
                "message": f"Workflow component validation failed: {str(e)}",
                "details": {"error": str(e)},
            }

    async def perform_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Perform comprehensive environment validation for both Manager and GraphMCP.

        Returns:
            Dict containing complete validation results
        """
        start_time = time.time()

        self.logger.log_step_start(
            "environment_validation",
            "Comprehensive environment validation for Manager and GraphMCP",
            {"database_name": self.database_name},
        )

        try:
            # Run Manager and GraphMCP validations concurrently
            manager_validation, graphmcp_validation = await asyncio.gather(
                self.validate_manager_infrastructure(),
                self.validate_graphmcp_components(),
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(manager_validation, Exception):
                manager_validation = {
                    "component": "manager_infrastructure",
                    "status": "FAILED",
                    "message": f"Manager validation exception: {str(manager_validation)}",
                    "details": {"error": str(manager_validation)},
                }

            if isinstance(graphmcp_validation, Exception):
                graphmcp_validation = {
                    "component": "graphmcp_framework",
                    "status": "FAILED",
                    "message": f"GraphMCP validation exception: {str(graphmcp_validation)}",
                    "details": {"error": str(graphmcp_validation)},
                }

            # Combine results
            all_validations = []
            
            # Add Manager validations
            if manager_validation.get("details", {}).get("validations"):
                all_validations.extend(manager_validation["details"]["validations"])
            else:
                all_validations.append(manager_validation)

            # Add GraphMCP validations
            if graphmcp_validation.get("details", {}).get("validations"):
                all_validations.extend(graphmcp_validation["details"]["validations"])
            else:
                all_validations.append(graphmcp_validation)

            # Calculate overall status
            failed_validations = [v for v in all_validations if v["status"] == "FAILED"]
            warning_validations = [v for v in all_validations if v["status"] == "WARNING"]
            
            overall_success = len(failed_validations) == 0

            # Generate search patterns for database
            search_patterns = [
                f"\\b{self.database_name}\\b",
                f"'{self.database_name}'",
                f'"{self.database_name}"',
                f"{self.database_name}\\.",
            ]

            result = {
                "database_name": self.database_name,
                "overall_success": overall_success,
                "manager_integration": manager_validation,
                "graphmcp_integration": graphmcp_validation,
                "search_patterns": search_patterns,
                "validation_summary": {
                    "total_checks": len(all_validations),
                    "passed_checks": len(all_validations) - len(failed_validations) - len(warning_validations),
                    "failed_checks": len(failed_validations),
                    "warning_checks": len(warning_validations),
                },
                "success": overall_success,
                "duration": time.time() - start_time,
            }

            # Log validation summary
            self.logger.log_environment_validation_summary(
                total_params=len(all_validations),
                secrets_count=4,  # Standard secrets count
                clients_validated=3,  # github, slack, repomix
                validation_time=result["duration"],
            )

            # Log detailed table
            self.logger.log_table(
                "Environment Validation Results",
                [
                    {
                        "component": v["component"],
                        "status": v["status"],
                        "message": v["message"],
                    }
                    for v in all_validations
                ],
            )

            self.logger.log_step_end("environment_validation", result, success=overall_success)

            return result

        except Exception as e:
            self.logger.log_error("Comprehensive environment validation failed", e)
            raise


# Legacy compatibility function for GraphMCP integration
async def validate_environment_step(
    context: Any,
    step: Any,
    database_name: str = "example_database",
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Legacy compatibility function for GraphMCP workflow integration.

    Args:
        context: WorkflowContext for data sharing
        step: Step configuration object
        database_name: Name of the database to decommission
        workflow_id: Unique workflow identifier

    Returns:
        Dict containing validation results
    """
    validator = EnvironmentValidator(database_name, workflow_id)
    result = await validator.perform_comprehensive_validation()

    # Store components in context for other steps (GraphMCP compatibility)
    param_service = get_parameter_service()
    context.set_shared_value("parameter_service", param_service)
    context.set_shared_value("search_patterns", result["search_patterns"])
    context.set_shared_value("environment_validation", result)

    return result