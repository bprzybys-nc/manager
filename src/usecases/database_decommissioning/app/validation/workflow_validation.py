"""
Workflow Validation for Database Decommissioning.

This module provides workflow-specific validation functionality enhanced for Manager integration
while preserving GraphMCP framework compatibility.

Manager Integration:
- Tenant and user context validation
- Manager-specific parameter validation
- Database workflow constraints

GraphMCP Preservation:
- Workflow parameter validation patterns
- Repository URL validation
- Search pattern generation
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

# Manager imports
import src.config as manager_config

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..models import WorkflowConfig, ValidationResult
from ..utils import extract_repo_details, is_manager_feature_enabled


class WorkflowValidator:
    """
    Workflow parameter validator with Manager integration.
    
    Validates workflow parameters, repository URLs, and Manager-specific constraints.
    """

    def __init__(self, workflow_id: Optional[str] = None):
        """
        Initialize workflow validator.

        Args:
            workflow_id: Optional workflow identifier
        """
        self.workflow_id = workflow_id or f"workflow_validation_{int(time.time())}"
        
        # Initialize logger
        config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id=self.workflow_id, config=config)

    def validate_database_name(self, database_name: str) -> Dict[str, Any]:
        """
        Validate database name format and constraints.

        Args:
            database_name: Database name to validate

        Returns:
            Dict containing validation results
        """
        try:
            validation_errors = []

            # Basic validation
            if not database_name or not database_name.strip():
                validation_errors.append("Database name cannot be empty")
            else:
                database_name = database_name.strip()

                # Length validation
                if len(database_name) < 2:
                    validation_errors.append("Database name must be at least 2 characters long")
                elif len(database_name) > 63:  # PostgreSQL limit
                    validation_errors.append("Database name must be 63 characters or less")

                # Character validation (allow alphanumeric, underscore, hyphen)
                if not re.match(r'^[a-zA-Z0-9_-]+$', database_name):
                    validation_errors.append("Database name can only contain letters, numbers, underscores, and hyphens")

                # Must start with letter or underscore
                if not re.match(r'^[a-zA-Z_]', database_name):
                    validation_errors.append("Database name must start with a letter or underscore")

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "component": "database_name",
                "status": "PASSED" if len(validation_errors) == 0 else "FAILED",
                "message": "Database name validation completed" if len(validation_errors) == 0 else f"Database name validation failed: {', '.join(validation_errors)}",
                "details": {
                    "database_name": database_name,
                    "length": len(database_name) if database_name else 0,
                    "errors": validation_errors,
                }
            }

        except Exception as e:
            self.logger.log_error("Database name validation failed", e)
            return {
                "valid": False,
                "errors": [f"Database name validation error: {str(e)}"],
                "component": "database_name",
                "status": "FAILED",
                "message": f"Database name validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    def validate_repository_urls(self, target_repos: List[str]) -> Dict[str, Any]:
        """
        Validate repository URLs and accessibility.

        Args:
            target_repos: List of repository URLs to validate

        Returns:
            Dict containing validation results
        """
        try:
            validation_errors = []
            validated_repos = []

            # Basic validation
            if not target_repos or len(target_repos) == 0:
                validation_errors.append("At least one target repository must be specified")
                return {
                    "valid": False,
                    "errors": validation_errors,
                    "component": "repository_urls",
                    "status": "FAILED",
                    "message": "Repository URL validation failed: no repositories specified",
                    "details": {"total_repos": 0, "errors": validation_errors},
                }

            # Validate each repository URL
            for i, repo_url in enumerate(target_repos):
                repo_validation = self._validate_single_repository_url(repo_url, i)
                
                if not repo_validation["valid"]:
                    validation_errors.extend(repo_validation["errors"])
                else:
                    validated_repos.append(repo_validation["details"])

            # Check for duplicates
            unique_repos = set(target_repos)
            if len(unique_repos) != len(target_repos):
                validation_errors.append("Duplicate repository URLs found")

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "component": "repository_urls",
                "status": "PASSED" if len(validation_errors) == 0 else "FAILED",
                "message": f"Repository URL validation completed: {len(validated_repos)}/{len(target_repos)} valid" if len(validation_errors) == 0 else f"Repository URL validation failed: {', '.join(validation_errors)}",
                "details": {
                    "total_repos": len(target_repos),
                    "valid_repos": len(validated_repos),
                    "validated_repos": validated_repos,
                    "errors": validation_errors,
                }
            }

        except Exception as e:
            self.logger.log_error("Repository URL validation failed", e)
            return {
                "valid": False,
                "errors": [f"Repository URL validation error: {str(e)}"],
                "component": "repository_urls",
                "status": "FAILED",
                "message": f"Repository URL validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    def _validate_single_repository_url(self, repo_url: str, index: int) -> Dict[str, Any]:
        """
        Validate a single repository URL.

        Args:
            repo_url: Repository URL to validate
            index: Index of the repository in the list

        Returns:
            Dict containing validation results for single repository
        """
        validation_errors = []

        if not repo_url or not repo_url.strip():
            validation_errors.append(f"Repository {index + 1}: URL cannot be empty")
            return {
                "valid": False,
                "errors": validation_errors,
                "details": {"index": index, "url": repo_url},
            }

        repo_url = repo_url.strip()

        # GitHub URL validation
        if not repo_url.startswith("https://github.com/"):
            validation_errors.append(f"Repository {index + 1}: Must be a GitHub HTTPS URL")
        else:
            # Extract and validate owner/repo format
            try:
                owner, repo_name = extract_repo_details(repo_url)
                
                if not owner or not repo_name:
                    validation_errors.append(f"Repository {index + 1}: Invalid GitHub URL format")
                elif owner == "bprzybys-nc" and repo_name == "postgres-sample-dbs":
                    # This is the default fallback, might indicate parsing failure
                    if repo_url != "https://github.com/bprzybys-nc/postgres-sample-dbs":
                        validation_errors.append(f"Repository {index + 1}: Could not parse owner/repository name")

                return {
                    "valid": len(validation_errors) == 0,
                    "errors": validation_errors,
                    "details": {
                        "index": index,
                        "url": repo_url,
                        "owner": owner,
                        "repo_name": repo_name,
                    },
                }
            except Exception as e:
                validation_errors.append(f"Repository {index + 1}: URL parsing failed - {str(e)}")

        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "details": {"index": index, "url": repo_url},
        }

    def validate_slack_configuration(self, slack_channel: str) -> Dict[str, Any]:
        """
        Validate Slack configuration and channel format.

        Args:
            slack_channel: Slack channel ID or name

        Returns:
            Dict containing validation results
        """
        try:
            validation_errors = []

            # Basic validation
            if not slack_channel or not slack_channel.strip():
                validation_errors.append("Slack channel cannot be empty")
            else:
                slack_channel = slack_channel.strip()

                # Channel format validation (either #channel-name or C1234567890)
                if not (slack_channel.startswith('#') or slack_channel.startswith('C')):
                    validation_errors.append("Slack channel must start with '#' (channel name) or 'C' (channel ID)")

                # Length validation
                if len(slack_channel) < 2:
                    validation_errors.append("Slack channel must be at least 2 characters long")

            # Check if Slack is enabled in Manager
            slack_enabled = is_manager_feature_enabled("slack")
            warning_messages = []
            
            if not slack_enabled:
                warning_messages.append("Slack integration not configured in Manager - notifications will be disabled")

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warning_messages,
                "component": "slack_configuration",
                "status": "PASSED" if len(validation_errors) == 0 else "FAILED",
                "message": "Slack configuration validation completed" if len(validation_errors) == 0 else f"Slack configuration validation failed: {', '.join(validation_errors)}",
                "details": {
                    "slack_channel": slack_channel,
                    "slack_enabled": slack_enabled,
                    "errors": validation_errors,
                    "warnings": warning_messages,
                }
            }

        except Exception as e:
            self.logger.log_error("Slack configuration validation failed", e)
            return {
                "valid": False,
                "errors": [f"Slack configuration validation error: {str(e)}"],
                "component": "slack_configuration",
                "status": "FAILED",
                "message": f"Slack configuration validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    def validate_manager_context(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate Manager-specific context parameters.

        Args:
            tenant_id: Optional tenant identifier
            user_id: Optional user identifier

        Returns:
            Dict containing validation results
        """
        try:
            validation_errors = []
            warnings = []

            # Tenant ID validation
            if tenant_id is not None:
                if not tenant_id.strip():
                    validation_errors.append("Tenant ID cannot be empty if provided")
                elif not re.match(r'^[a-zA-Z0-9_-]+$', tenant_id.strip()):
                    validation_errors.append("Tenant ID can only contain letters, numbers, underscores, and hyphens")

            # User ID validation
            if user_id is not None:
                if not user_id.strip():
                    validation_errors.append("User ID cannot be empty if provided")
                elif not re.match(r'^[a-zA-Z0-9_@.-]+$', user_id.strip()):
                    validation_errors.append("User ID format is invalid")

            # Manager feature availability
            manager_features = {
                "mongodb": is_manager_feature_enabled("mongodb"),
                "azure_openai": is_manager_feature_enabled("azure_openai"),
                "prometheus": is_manager_feature_enabled("prometheus"),
                "celery": is_manager_feature_enabled("celery"),
            }

            # Check for missing critical features
            if not manager_features["mongodb"]:
                validation_errors.append("Manager MongoDB integration not configured - required for state management")

            if not manager_features["azure_openai"]:
                validation_errors.append("Manager Azure OpenAI integration not configured - required for AI processing")

            # Non-critical features
            if not manager_features["prometheus"]:
                warnings.append("Prometheus monitoring not configured - metrics collection will be limited")

            if not manager_features["celery"]:
                warnings.append("Celery workers not configured - background processing may be limited")

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "component": "manager_context",
                "status": "PASSED" if len(validation_errors) == 0 else "FAILED",
                "message": "Manager context validation completed" if len(validation_errors) == 0 else f"Manager context validation failed: {', '.join(validation_errors)}",
                "details": {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "manager_features": manager_features,
                    "errors": validation_errors,
                    "warnings": warnings,
                }
            }

        except Exception as e:
            self.logger.log_error("Manager context validation failed", e)
            return {
                "valid": False,
                "errors": [f"Manager context validation error: {str(e)}"],
                "component": "manager_context",
                "status": "FAILED",
                "message": f"Manager context validation error: {str(e)}",
                "details": {"error": str(e)},
            }

    def validate_workflow_configuration(self, config: WorkflowConfig) -> Dict[str, Any]:
        """
        Validate complete workflow configuration.

        Args:
            config: Workflow configuration to validate

        Returns:
            Dict containing comprehensive validation results
        """
        start_time = time.time()

        self.logger.log_step_start(
            "workflow_validation",
            "Comprehensive workflow configuration validation",
            {"database_name": config.database_name},
        )

        try:
            validations = []

            # Validate database name
            db_validation = self.validate_database_name(config.database_name)
            validations.append(db_validation)

            # Validate repository URLs (create from repo_owner/repo_name)
            repo_url = f"https://github.com/{config.repo_owner}/{config.repo_name}"
            repo_validation = self.validate_repository_urls([repo_url])
            validations.append(repo_validation)

            # Validate Slack configuration (use default if not in config)
            slack_channel = getattr(config, 'slack_channel', 'demo-channel')
            slack_validation = self.validate_slack_configuration(slack_channel)
            validations.append(slack_validation)

            # Validate Manager context
            manager_validation = self.validate_manager_context(config.tenant_id, config.user_id)
            validations.append(manager_validation)

            # Validate workflow parameters
            params_validation = self._validate_workflow_parameters(config)
            validations.append(params_validation)

            # Calculate overall results
            failed_validations = [v for v in validations if v["status"] == "FAILED"]
            warning_validations = [v for v in validations if v["status"] == "WARNING"]
            
            overall_success = len(failed_validations) == 0
            all_errors = []
            all_warnings = []

            for validation in validations:
                all_errors.extend(validation.get("errors", []))
                all_warnings.extend(validation.get("warnings", []))

            result = {
                "workflow_id": self.workflow_id,
                "database_name": config.database_name,
                "overall_success": overall_success,
                "validations": validations,
                "validation_summary": {
                    "total_checks": len(validations),
                    "passed_checks": len(validations) - len(failed_validations) - len(warning_validations),
                    "failed_checks": len(failed_validations),
                    "warning_checks": len(warning_validations),
                },
                "all_errors": all_errors,
                "all_warnings": all_warnings,
                "success": overall_success,
                "duration": time.time() - start_time,
            }

            # Log validation summary
            self.logger.log_table(
                "Workflow Configuration Validation Results",
                [
                    {
                        "component": v["component"],
                        "status": v["status"],
                        "message": v["message"],
                    }
                    for v in validations
                ],
            )

            self.logger.log_step_end("workflow_validation", result, success=overall_success)

            return result

        except Exception as e:
            self.logger.log_error("Workflow configuration validation failed", e)
            raise

    def _validate_workflow_parameters(self, config: WorkflowConfig) -> Dict[str, Any]:
        """
        Validate workflow-specific parameters.

        Args:
            config: Workflow configuration

        Returns:
            Dict containing parameter validation results
        """
        try:
            validation_errors = []
            warnings = []

            # Validate parallel steps
            if config.max_parallel_steps < 1:
                validation_errors.append("Maximum parallel steps must be at least 1")
            elif config.max_parallel_steps > 10:
                warnings.append("Maximum parallel steps is quite high (>10) - may impact performance")

            # Validate timeout
            if config.default_timeout < 30:
                validation_errors.append("Default timeout must be at least 30 seconds")
            elif config.default_timeout > 600:
                warnings.append("Default timeout is quite high (>10 minutes) - may cause delays")

            # Validate log file path
            if config.log_file and not config.log_file.strip():
                validation_errors.append("Log file path cannot be empty if provided")

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "component": "workflow_parameters",
                "status": "PASSED" if len(validation_errors) == 0 else "FAILED",
                "message": "Workflow parameters validation completed" if len(validation_errors) == 0 else f"Workflow parameters validation failed: {', '.join(validation_errors)}",
                "details": {
                    "max_parallel_steps": config.max_parallel_steps,
                    "default_timeout": config.default_timeout,
                    "log_file": config.log_file,
                    "dry_run": config.dry_run,
                    "errors": validation_errors,
                    "warnings": warnings,
                }
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Workflow parameters validation error: {str(e)}"],
                "component": "workflow_parameters",
                "status": "FAILED",
                "message": f"Workflow parameters validation error: {str(e)}",
                "details": {"error": str(e)},
            }


# Legacy compatibility functions for GraphMCP integration
def validate_workflow_parameters(
    database_name: str,
    target_repos: List[str],
    slack_channel: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Legacy compatibility function for parameter validation.

    Args:
        database_name: Name of the database to decommission
        target_repos: List of repository URLs to process
        slack_channel: Slack channel ID for notifications
        tenant_id: Optional tenant identifier

    Returns:
        Dict containing validation results
    """
    validator = WorkflowValidator()
    
    # Perform individual validations
    db_validation = validator.validate_database_name(database_name)
    repo_validation = validator.validate_repository_urls(target_repos)
    slack_validation = validator.validate_slack_configuration(slack_channel)
    manager_validation = validator.validate_manager_context(tenant_id)

    # Combine results
    all_errors = []
    all_errors.extend(db_validation.get("errors", []))
    all_errors.extend(repo_validation.get("errors", []))
    all_errors.extend(slack_validation.get("errors", []))
    all_errors.extend(manager_validation.get("errors", []))

    return {"valid": len(all_errors) == 0, "errors": all_errors}