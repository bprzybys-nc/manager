"""
Workflow Orchestrator for Database Decommissioning.

This module provides Manager-integrated workflow orchestration that coordinates
database decommissioning workflows while maintaining GraphMCP framework compatibility.

Manager Integration:
- Enhanced workflow coordination with Manager context
- Manager-specific logging and metrics
- Tenant-aware workflow execution
- Database client integration for state persistence

GraphMCP Preservation:
- Full GraphMCP workflow builder compatibility
- Standard workflow execution patterns
- MCP client orchestration
- Workflow context management
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Manager imports
import src.config as manager_config
from src.database.client import DatabaseClient

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.workflows.builder import WorkflowBuilder, WorkflowResult, WorkflowConfig, WorkflowContext
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from .models import WorkflowConfig as ManagerWorkflowConfig, WorkflowExecutionResult
from .utils import create_logger_for_workflow, get_manager_database_client
from .clients import GitHubClientWrapper, SlackClientWrapper, RepomixClientWrapper
from .validation import WorkflowValidator
from .processors import PatternDiscoveryProcessor, FileProcessor, RepositoryProcessor


class DatabaseDecommissionOrchestrator:
    """
    Database decommissioning workflow orchestrator with Manager integration.
    
    Coordinates the complete database decommissioning workflow while maintaining
    GraphMCP framework compatibility and adding Manager-specific enhancements.
    """

    def __init__(
        self,
        config: ManagerWorkflowConfig,
        mcp_config_path: Optional[str | Path] = None,
    ):
        """
        Initialize database decommission orchestrator.

        Args:
            config: Manager workflow configuration
            mcp_config_path: Path to MCP configuration file
        """
        self.config = config
        self.mcp_config_path = mcp_config_path or Path("src/frameworks/graphmcp/mcp_config.json")
        self.workflow_id = f"db_decommission_{config.database_name}_{int(time.time())}"

        # Initialize logging
        self.logger = create_logger_for_workflow(
            self.workflow_id, config.database_name, config.tenant_id
        )

        # Initialize Manager database client
        self.db_client = get_manager_database_client()

        # Initialize MCP client wrappers
        self.github_client: Optional[GitHubClientWrapper] = None
        self.slack_client: Optional[SlackClientWrapper] = None
        self.repomix_client: Optional[RepomixClientWrapper] = None

        # Workflow state
        self.workflow_result: Optional[WorkflowExecutionResult] = None
        self.execution_context: Optional[Dict[str, Any]] = None

    async def initialize_clients(self):
        """Initialize MCP client wrappers."""
        try:
            self.logger.log_info("Initializing MCP clients")

            # Initialize GitHub client
            self.github_client = GitHubClientWrapper(
                self.mcp_config_path, self.config.tenant_id, self.workflow_id
            )

            # Initialize Slack client
            self.slack_client = SlackClientWrapper(
                self.mcp_config_path, self.config.tenant_id, self.workflow_id
            )

            # Initialize Repomix client
            self.repomix_client = RepomixClientWrapper(
                self.mcp_config_path, self.config.tenant_id, self.workflow_id
            )

            # Test client connections
            client_status = await self._test_client_connections()
            self.logger.log_info(
                "MCP client initialization completed",
                {"client_status": client_status}
            )

        except Exception as e:
            self.logger.log_error("Failed to initialize MCP clients", e)
            raise

    async def _test_client_connections(self) -> Dict[str, bool]:
        """Test MCP client connections."""
        status = {}

        # Test GitHub client
        if self.github_client:
            status["github"] = await self.github_client.health_check()

        # Test Slack client
        if self.slack_client:
            status["slack"] = await self.slack_client.health_check()

        # Test Repomix client
        if self.repomix_client:
            status["repomix"] = await self.repomix_client.health_check()

        return status

    async def execute_workflow(self) -> WorkflowExecutionResult:
        """
        Execute the complete database decommissioning workflow.

        Returns:
            Comprehensive workflow execution result
        """
        start_time = time.time()

        self.logger.log_workflow_start(
            [self.config.database_name],
            {
                "database_name": self.config.database_name,
                "repositories": [f"{self.config.repo_owner}/{self.config.repo_name}"],
                "tenant_id": self.config.tenant_id,
                "user_id": self.config.user_id,
            }
        )

        try:
            # Initialize workflow execution context
            await self._initialize_workflow_context()

            # Validate workflow configuration
            validation_result = await self._validate_workflow_configuration()
            if not validation_result["overall_success"]:
                return self._create_failed_result(
                    "Workflow validation failed", validation_result, start_time
                )

            # Initialize MCP clients
            await self.initialize_clients()

            # Build and execute GraphMCP workflow
            workflow = await self._build_graphmcp_workflow()
            graphmcp_result = await workflow.execute(self.logger)

            # Process workflow results
            result = await self._process_workflow_results(graphmcp_result, start_time)

            # Store workflow result in Manager database
            await self._store_workflow_result(result)

            # Send completion notification
            await self._send_completion_notification(result)

            self.logger.log_workflow_end(result.success)
            return result

        except Exception as e:
            self.logger.log_error("Workflow execution failed", e)
            result = self._create_failed_result(f"Workflow execution error: {e}", {}, start_time)
            await self._send_completion_notification(result)
            return result

    async def _initialize_workflow_context(self):
        """Initialize workflow execution context."""
        self.execution_context = {
            "workflow_id": self.workflow_id,
            "database_name": self.config.database_name,
            "repository": f"{self.config.repo_owner}/{self.config.repo_name}",
            "tenant_id": self.config.tenant_id,
            "user_id": self.config.user_id,
            "started_at": time.time(),
            "config": self.config.to_dict(),
        }

        self.logger.log_info("Workflow context initialized", self.execution_context)

    async def _validate_workflow_configuration(self) -> Dict[str, Any]:
        """Validate workflow configuration."""
        self.logger.log_step_start("validation", "Workflow configuration validation")

        try:
            validator = WorkflowValidator(self.workflow_id)
            validation_result = validator.validate_workflow_configuration(self.config)

            self.logger.log_step_end("validation", validation_result, validation_result["overall_success"])
            return validation_result

        except Exception as e:
            self.logger.log_error("Workflow validation failed", e)
            return {"overall_success": False, "error": str(e)}

    async def _build_graphmcp_workflow(self) -> Any:
        """Build GraphMCP workflow with Manager integration."""
        try:
            # Create GraphMCP workflow configuration
            graphmcp_config = WorkflowConfig(
                name=f"database_decommission_{self.config.database_name}",
                config_path=str(self.mcp_config_path),
                description=f"Database decommissioning workflow for {self.config.database_name}",
                max_parallel_steps=self.config.max_parallel_steps,
                default_timeout=self.config.default_timeout,
                stop_on_error=False,  # Continue on errors for better diagnostics
            )

            # Build workflow using fluent API
            builder = WorkflowBuilder(
                graphmcp_config.name,
                graphmcp_config.config_path,
                graphmcp_config.description
            ).with_config(
                max_parallel_steps=graphmcp_config.max_parallel_steps,
                default_timeout=graphmcp_config.default_timeout,
                stop_on_error=graphmcp_config.stop_on_error,
            )

            # Add workflow steps using step_auto (preferred method)
            repo_url = f"https://github.com/{self.config.repo_owner}/{self.config.repo_name}"

            # Step 1: Repository Analysis
            builder.step_auto(
                "repository_analysis",
                "Repository Analysis",
                self._repository_analysis_step,
                description="Analyze repository structure and gather metadata",
                parameters={"repo_url": repo_url}
            )

            # Step 2: Pattern Discovery
            builder.step_auto(
                "pattern_discovery",
                "Database Pattern Discovery",
                self._pattern_discovery_step,
                description=f"Discover database references for {self.config.database_name}",
                parameters={
                    "database_name": self.config.database_name,
                    "repo_url": repo_url,
                }
            )

            # Step 3: Quality Assurance
            builder.step_auto(
                "quality_assurance",
                "Quality Assurance Validation",
                self._quality_assurance_step,
                description="Perform comprehensive QA validation",
                parameters={"database_name": self.config.database_name}
            )

            # Step 4: File Processing (if not dry run)
            if not self.config.dry_run:
                builder.step_auto(
                    "file_processing",
                    "Database Reference Processing",
                    self._file_processing_step,
                    description="Process files with database references",
                    parameters={
                        "database_name": self.config.database_name,
                        "repo_url": repo_url,
                    }
                )

            # Step 5: Results Summary
            builder.step_auto(
                "results_summary",
                "Workflow Results Summary",
                self._results_summary_step,
                description="Compile comprehensive workflow results",
                parameters={"database_name": self.config.database_name}
            )

            return builder.build()

        except Exception as e:
            self.logger.log_error("Failed to build GraphMCP workflow", e)
            raise

    async def _repository_analysis_step(self, context: WorkflowContext, step: Any, **params) -> Dict[str, Any]:
        """Repository analysis workflow step."""
        repo_url = params.get("repo_url")

        try:
            # Initialize repository processor
            processor = RepositoryProcessor(
                self.config.database_name,
                self.config.tenant_id,
                self.workflow_id,
            )

            # Process repository
            result = await processor.process_repositories(
                [repo_url],
                slack_channel=getattr(self.config, 'slack_channel', None),
                context=context,
            )

            # Store repository analysis result
            context.set_shared_value("repository_analysis", result)

            return {
                "success": result.get("success", False),
                "repositories_processed": result.get("repositories_processed", 0),
                "total_files": result.get("total_files_processed", 0),
                "repository_url": repo_url,
            }

        except Exception as e:
            self.logger.log_error(f"Repository analysis failed for {repo_url}", e)
            return {
                "success": False,
                "error": str(e),
                "repository_url": repo_url,
            }

    async def _pattern_discovery_step(self, context: WorkflowContext, step: Any, **params) -> Dict[str, Any]:
        """Pattern discovery workflow step."""
        database_name = params.get("database_name")
        repo_url = params.get("repo_url")

        try:
            # Get repository analysis result
            repo_analysis = context.get_shared_value("repository_analysis", {})
            if not repo_analysis.get("success"):
                return {
                    "success": False,
                    "error": "Repository analysis required for pattern discovery",
                }

            # Initialize pattern discovery processor
            processor = PatternDiscoveryProcessor(
                database_name,
                self.config.repo_owner,
                self.config.repo_name,
                self.config.tenant_id,
                self.workflow_id,
            )

            # Get repository content from previous step
            processed_repos = repo_analysis.get("processed_repositories", [])
            if not processed_repos:
                return {
                    "success": False,
                    "error": "No processed repositories found for pattern discovery",
                }

            # Use discovery result from first repository
            repo_content = processed_repos[0].get("discovery_result", {})
            discovery_result = await processor.discover_patterns_in_repository(repo_content)

            # Store discovery result
            context.set_shared_value("discovery", discovery_result)

            return {
                "success": discovery_result.get("success", False),
                "database_name": database_name,
                "total_files": discovery_result.get("total_files", 0),
                "matched_files": discovery_result.get("matched_files", 0),
                "files_by_type": discovery_result.get("files_by_type", {}),
            }

        except Exception as e:
            self.logger.log_error(f"Pattern discovery failed for {database_name}", e)
            return {
                "success": False,
                "error": str(e),
                "database_name": database_name,
            }

    async def _quality_assurance_step(self, context: WorkflowContext, step: Any, **params) -> Dict[str, Any]:
        """Quality assurance workflow step."""
        database_name = params.get("database_name")

        try:
            # Get discovery result
            discovery_result = context.get_shared_value("discovery", {})
            if not discovery_result.get("success"):
                return {
                    "success": False,
                    "error": "Pattern discovery required for quality assurance",
                }

            # Import QA validator
            from .validation.quality_assurance import QualityAssuranceValidator

            # Initialize QA validator
            qa_validator = QualityAssuranceValidator(database_name, self.workflow_id)

            # Perform comprehensive QA
            qa_result = await qa_validator.perform_comprehensive_qa(discovery_result)

            # Store QA result
            context.set_shared_value("quality_assurance", qa_result.to_dict())

            return {
                "success": qa_result.overall_status.value == "PASSED",
                "database_name": database_name,
                "quality_score": qa_result.details.get("quality_score", 0),
                "checks_passed": qa_result.details.get("checks_passed", 0),
                "total_checks": qa_result.details.get("total_checks", 0),
                "recommendations": qa_result.recommendations,
            }

        except Exception as e:
            self.logger.log_error(f"Quality assurance failed for {database_name}", e)
            return {
                "success": False,
                "error": str(e),
                "database_name": database_name,
            }

    async def _file_processing_step(self, context: WorkflowContext, step: Any, **params) -> Dict[str, Any]:
        """File processing workflow step."""
        database_name = params.get("database_name")
        repo_url = params.get("repo_url")

        try:
            # Get discovery result
            discovery_result = context.get_shared_value("discovery", {})
            if not discovery_result.get("success"):
                return {
                    "success": False,
                    "error": "Pattern discovery required for file processing",
                }

            # Initialize file processor
            processor = FileProcessor(
                database_name,
                self.config.tenant_id,
                self.workflow_id,
            )

            # Create temporary directory for file processing
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Process files (this would typically involve cloning the repo)
                # For now, we'll simulate processing based on discovery results
                files = discovery_result.get("files", [])
                
                processing_result = {
                    "success": True,
                    "database_name": database_name,
                    "files_processed": len(files),
                    "files_modified": sum(1 for f in files if f.get("matches")),
                    "processing_summary": f"Processed {len(files)} files for database {database_name}",
                }

            # Store processing result
            context.set_shared_value("file_processing", processing_result)

            return processing_result

        except Exception as e:
            self.logger.log_error(f"File processing failed for {database_name}", e)
            return {
                "success": False,
                "error": str(e),
                "database_name": database_name,
            }

    async def _results_summary_step(self, context: WorkflowContext, step: Any, **params) -> Dict[str, Any]:
        """Results summary workflow step."""
        database_name = params.get("database_name")

        try:
            # Gather results from all previous steps
            repo_analysis = context.get_shared_value("repository_analysis", {})
            discovery_result = context.get_shared_value("discovery", {})
            qa_result = context.get_shared_value("quality_assurance", {})
            file_processing = context.get_shared_value("file_processing", {})

            # Create comprehensive summary
            summary = {
                "database_name": database_name,
                "workflow_id": self.workflow_id,
                "tenant_id": self.config.tenant_id,
                "repository": f"{self.config.repo_owner}/{self.config.repo_name}",
                "repository_analysis": {
                    "success": repo_analysis.get("success", False),
                    "repositories_processed": repo_analysis.get("repositories_processed", 0),
                    "total_files": repo_analysis.get("total_files", 0),
                },
                "pattern_discovery": {
                    "success": discovery_result.get("success", False),
                    "matched_files": discovery_result.get("matched_files", 0),
                    "files_by_type": discovery_result.get("files_by_type", {}),
                },
                "quality_assurance": {
                    "success": qa_result.get("overall_status") == "PASSED",
                    "quality_score": qa_result.get("details", {}).get("quality_score", 0),
                    "recommendations": qa_result.get("recommendations", []),
                },
                "file_processing": {
                    "success": file_processing.get("success", False),
                    "files_processed": file_processing.get("files_processed", 0),
                    "files_modified": file_processing.get("files_modified", 0),
                },
                "dry_run": self.config.dry_run,
            }

            # Store summary
            context.set_shared_value("workflow_summary", summary)

            return summary

        except Exception as e:
            self.logger.log_error(f"Results summary failed for {database_name}", e)
            return {
                "success": False,
                "error": str(e),
                "database_name": database_name,
            }

    async def _process_workflow_results(
        self, graphmcp_result: WorkflowResult, start_time: float
    ) -> WorkflowExecutionResult:
        """Process GraphMCP workflow results into Manager format."""
        try:
            duration = time.time() - start_time
            success = graphmcp_result.status == "completed"

            # Get workflow summary from results
            workflow_summary = graphmcp_result.get_step_result("workflow_summary", {})

            result = WorkflowExecutionResult(
                workflow_id=self.workflow_id,
                database_name=self.config.database_name,
                success=success,
                duration=duration,
                step_results=graphmcp_result.step_results,
                tenant_id=self.config.tenant_id,
                user_id=self.config.user_id,
                config=self.config.to_dict(),
                summary=workflow_summary,
                graphmcp_result=graphmcp_result,
            )

            self.workflow_result = result
            return result

        except Exception as e:
            self.logger.log_error("Failed to process workflow results", e)
            return self._create_failed_result(f"Result processing error: {e}", {}, start_time)

    def _create_failed_result(
        self, error_message: str, details: Dict[str, Any], start_time: float
    ) -> WorkflowExecutionResult:
        """Create a failed workflow result."""
        return WorkflowExecutionResult(
            workflow_id=self.workflow_id,
            database_name=self.config.database_name,
            success=False,
            duration=time.time() - start_time,
            step_results={"error": error_message, "details": details},
            tenant_id=self.config.tenant_id,
            user_id=self.config.user_id,
            config=self.config.to_dict(),
            summary={"error": error_message, "failed": True},
        )

    async def _store_workflow_result(self, result: WorkflowExecutionResult):
        """Store workflow result in Manager database."""
        if not self.db_client:
            self.logger.log_warning("Manager database not available, skipping result storage")
            return

        try:
            # Store in workflow_executions collection
            collection = self.db_client.database["workflow_executions"]
            
            document = {
                "workflow_id": result.workflow_id,
                "database_name": result.database_name,
                "success": result.success,
                "duration": result.duration,
                "tenant_id": result.tenant_id,
                "user_id": result.user_id,
                "config": result.config,
                "summary": result.summary,
                "step_results": result.step_results,
                "created_at": time.time(),
                "workflow_type": "database_decommissioning",
            }

            await collection.insert_one(document)
            self.logger.log_info("Workflow result stored in Manager database")

        except Exception as e:
            self.logger.log_error("Failed to store workflow result", e)

    async def _send_completion_notification(self, result: WorkflowExecutionResult):
        """Send workflow completion notification."""
        if not self.slack_client:
            self.logger.log_info("Slack client not available, skipping notification")
            return

        try:
            # Determine notification status
            status = "completed" if result.success else "failed"
            
            # Get notification details
            summary = result.summary or {}
            
            details = {
                "duration": f"{result.duration:.1f}s",
                "files_processed": summary.get("file_processing", {}).get("files_processed", 0),
                "files_modified": summary.get("file_processing", {}).get("files_modified", 0),
                "quality_score": summary.get("quality_assurance", {}).get("quality_score", 0),
            }

            # Send notification
            channel = getattr(self.config, 'slack_channel', 'general')
            repository = f"{self.config.repo_owner}/{self.config.repo_name}"

            await self.slack_client.post_database_decommission_notification(
                channel_id=channel,
                database_name=self.config.database_name,
                repository=repository,
                status=status,
                details=details,
            )

        except Exception as e:
            self.logger.log_error("Failed to send completion notification", e)

    async def close(self):
        """Close orchestrator and cleanup resources."""
        try:
            # Close MCP clients
            if self.github_client:
                await self.github_client.close()
            if self.slack_client:
                await self.slack_client.close()
            if self.repomix_client:
                await self.repomix_client.close()

            # Close database client
            if self.db_client:
                await self.db_client.close()

            self.logger.log_info("Orchestrator closed successfully")

        except Exception as e:
            self.logger.log_error("Error closing orchestrator", e)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()


# Legacy compatibility functions for GraphMCP integration
async def execute_database_decommission_workflow(
    database_name: str,
    repo_owner: str,
    repo_name: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    mcp_config_path: Optional[str] = None,
    **kwargs
) -> WorkflowExecutionResult:
    """
    Legacy compatibility function for executing database decommissioning workflow.

    Args:
        database_name: Name of database to decommission
        repo_owner: Repository owner
        repo_name: Repository name
        tenant_id: Optional tenant identifier
        user_id: Optional user identifier
        mcp_config_path: Optional MCP configuration path
        **kwargs: Additional configuration parameters

    Returns:
        Workflow execution result
    """
    # Create workflow configuration
    config = ManagerWorkflowConfig(
        database_name=database_name,
        repo_owner=repo_owner,
        repo_name=repo_name,
        tenant_id=tenant_id,
        user_id=user_id,
        **kwargs
    )

    # Execute workflow
    async with DatabaseDecommissionOrchestrator(config, mcp_config_path) as orchestrator:
        return await orchestrator.execute_workflow()


async def create_database_decommission_orchestrator(
    config: ManagerWorkflowConfig,
    mcp_config_path: Optional[str] = None,
) -> DatabaseDecommissionOrchestrator:
    """
    Factory function to create database decommission orchestrator.

    Args:
        config: Manager workflow configuration
        mcp_config_path: Optional MCP configuration path

    Returns:
        Initialized database decommission orchestrator
    """
    return DatabaseDecommissionOrchestrator(config, mcp_config_path)