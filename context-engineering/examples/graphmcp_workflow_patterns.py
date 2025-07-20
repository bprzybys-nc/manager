"""
GraphMCP Workflow Patterns - Manager Component Examples

This file demonstrates patterns for creating and managing GraphMCP workflows
within the Ovora Manager component.
"""

from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import logging

from frameworks.graphmcp.workflows.builder import WorkflowBuilder
from frameworks.graphmcp.workflows.context import WorkflowContext
from frameworks.graphmcp.clients.github import GitHubMCPClient
from frameworks.graphmcp.clients.slack import SlackMCPClient
from frameworks.graphmcp.clients.repomix import RepomixMCPClient
from frameworks.graphmcp.clients.filesystem import FilesystemMCPClient
from frameworks.graphmcp.utils.config import ParameterService
from frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseDecommissionWorkflow:
    """
    Example workflow for database decommissioning using GraphMCP framework.
    
    This demonstrates the preferred patterns for manager component workflows:
    - Multi-client orchestration
    - Error handling and graceful degradation
    - Structured logging
    - Strategy-based processing
    """
    
    def __init__(self, config_path: str):
        """Initialize workflow with configuration."""
        self.config_path = config_path
        self.parameter_service = ParameterService(config_path)
        
        # Setup logging
        logging_config = LoggingConfig.from_env()
        self.logger = get_logger(
            workflow_id="db_decommission",
            config=logging_config
        )
    
    async def execute(self, database_name: str, repository_url: str) -> Dict[str, Any]:
        """
        Execute database decommissioning workflow.
        
        Args:
            database_name: Name of database to decommission
            repository_url: GitHub repository URL to analyze
            
        Returns:
            Workflow execution results
        """
        try:
            self.logger.log_workflow_start({
                "database_name": database_name,
                "repository_url": repository_url
            }, self.parameter_service.get_config())
            
            # Build workflow using preferred patterns
            workflow = (WorkflowBuilder("db_decommission", self.config_path)
                .with_config(max_parallel_steps=4, default_timeout=120)
                .step_auto("validate_inputs", "Validate inputs", self._validate_inputs)
                .step_auto("analyze_repository", "Analyze repository", self._analyze_repository)
                .step_auto("find_references", "Find database references", self._find_database_references)
                .step_auto("create_refactor_plan", "Create refactoring plan", self._create_refactor_plan)
                .step_auto("execute_refactoring", "Execute refactoring", self._execute_refactoring)
                .step_auto("create_pull_request", "Create pull request", self._create_pull_request)
                .step_auto("notify_stakeholders", "Notify stakeholders", self._notify_stakeholders)
                .build())
            
            # Execute workflow
            result = await workflow.execute({
                "database_name": database_name,
                "repository_url": repository_url
            })
            
            self.logger.log_workflow_end("db_decommission", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Workflow failed", exception=e)
            return {"success": False, "error": str(e)}
    
    async def _validate_inputs(self, context: WorkflowContext) -> Dict[str, Any]:
        """Validate workflow inputs."""
        self.logger.log_step_start("validate_inputs", "Validating workflow inputs")
        
        try:
            database_name = context.get_parameter("database_name")
            repository_url = context.get_parameter("repository_url")
            
            if not database_name or not repository_url:
                raise ValueError("Database name and repository URL are required")
            
            # Additional validation logic
            if len(database_name) < 3:
                raise ValueError("Database name must be at least 3 characters")
            
            result = {
                "database_name": database_name,
                "repository_url": repository_url,
                "validated": True
            }
            
            self.logger.log_step_end("validate_inputs", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Input validation failed", exception=e)
            self.logger.log_step_end("validate_inputs", {}, success=False)
            raise
    
    async def _analyze_repository(self, context: WorkflowContext) -> Dict[str, Any]:
        """Analyze repository using Repomix client."""
        self.logger.log_step_start("analyze_repository", "Analyzing repository structure")
        
        try:
            # Get or create Repomix client
            repomix_client = self._get_repomix_client(context)
            
            repository_url = context.get_parameter("repository_url")
            
            # Pack repository for analysis
            pack_result = await repomix_client.pack_remote_repository(
                remote=repository_url,
                compress=True  # Use compression for large repositories
            )
            
            # Store output ID for later use
            context.set_parameter("repomix_output_id", pack_result["output_id"])
            
            result = {
                "output_id": pack_result["output_id"],
                "file_count": pack_result.get("file_count", 0),
                "analysis_complete": True
            }
            
            self.logger.log_step_end("analyze_repository", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Repository analysis failed", exception=e)
            self.logger.log_step_end("analyze_repository", {}, success=False)
            raise
    
    async def _find_database_references(self, context: WorkflowContext) -> Dict[str, Any]:
        """Find database references in code."""
        self.logger.log_step_start("find_references", "Finding database references")
        
        try:
            repomix_client = self._get_repomix_client(context)
            database_name = context.get_parameter("database_name")
            output_id = context.get_parameter("repomix_output_id")
            
            # Search for database references
            search_patterns = [
                database_name,
                f'"{database_name}"',
                f"'{database_name}'",
                f"database.*{database_name}",
                f"db.*{database_name}"
            ]
            
            references = []
            for pattern in search_patterns:
                search_result = await repomix_client.grep_repomix_output(
                    output_id=output_id,
                    pattern=pattern,
                    context_lines=3,
                    ignore_case=True
                )
                
                if search_result.get("matches"):
                    references.extend(search_result["matches"])
            
            # Deduplicate and categorize references
            unique_references = self._categorize_references(references)
            
            result = {
                "total_references": len(references),
                "unique_references": len(unique_references),
                "categorized_references": unique_references
            }
            
            self.logger.log_table("Database References Found", [
                {"File": ref["file"], "Line": ref["line"], "Type": ref["category"]}
                for ref in unique_references[:10]  # Show first 10
            ])
            
            self.logger.log_step_end("find_references", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Reference finding failed", exception=e)
            self.logger.log_step_end("find_references", {}, success=False)
            raise
    
    async def _create_refactor_plan(self, context: WorkflowContext) -> Dict[str, Any]:
        """Create refactoring plan based on found references."""
        self.logger.log_step_start("create_refactor_plan", "Creating refactoring plan")
        
        try:
            references = context.get_parameter("categorized_references", [])
            
            # Group references by strategy
            plan = {
                "configuration_files": [],
                "code_files": [],
                "documentation_files": [],
                "infrastructure_files": []
            }
            
            for ref in references:
                strategy = self._determine_strategy(ref["file"])
                if strategy in plan:
                    plan[strategy].append(ref)
            
            # Create action items
            action_items = []
            for strategy, refs in plan.items():
                if refs:
                    action_items.append({
                        "strategy": strategy,
                        "file_count": len(refs),
                        "files": [ref["file"] for ref in refs],
                        "priority": self._get_strategy_priority(strategy)
                    })
            
            # Sort by priority
            action_items.sort(key=lambda x: x["priority"])
            
            result = {
                "plan": plan,
                "action_items": action_items,
                "total_files": sum(len(refs) for refs in plan.values())
            }
            
            self.logger.log_step_end("create_refactor_plan", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Plan creation failed", exception=e)
            self.logger.log_step_end("create_refactor_plan", {}, success=False)
            raise
    
    async def _execute_refactoring(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute refactoring based on plan."""
        self.logger.log_step_start("execute_refactoring", "Executing refactoring")
        
        try:
            github_client = self._get_github_client(context)
            action_items = context.get_parameter("action_items", [])
            repository_url = context.get_parameter("repository_url")
            
            # Extract owner/repo from URL
            repo_parts = repository_url.split("/")
            owner, repo = repo_parts[-2], repo_parts[-1].replace(".git", "")
            
            # Create feature branch
            branch_name = f"decommission-{context.get_parameter('database_name')}"
            await github_client.create_branch(
                owner=owner,
                repo=repo,
                branch=branch_name
            )
            
            # Process each action item
            changes_made = []
            for item in action_items:
                try:
                    changes = await self._process_action_item(
                        github_client, owner, repo, branch_name, item
                    )
                    changes_made.extend(changes)
                except Exception as e:
                    self.logger.log_error(f"Failed to process {item['strategy']}", exception=e)
                    continue
            
            result = {
                "branch_created": branch_name,
                "changes_made": len(changes_made),
                "files_modified": changes_made
            }
            
            context.set_parameter("refactor_branch", branch_name)
            context.set_parameter("changes_made", changes_made)
            
            self.logger.log_step_end("execute_refactoring", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Refactoring execution failed", exception=e)
            self.logger.log_step_end("execute_refactoring", {}, success=False)
            raise
    
    async def _create_pull_request(self, context: WorkflowContext) -> Dict[str, Any]:
        """Create pull request for changes."""
        self.logger.log_step_start("create_pull_request", "Creating pull request")
        
        try:
            github_client = self._get_github_client(context)
            repository_url = context.get_parameter("repository_url")
            database_name = context.get_parameter("database_name")
            branch_name = context.get_parameter("refactor_branch")
            changes_made = context.get_parameter("changes_made", [])
            
            # Extract owner/repo from URL
            repo_parts = repository_url.split("/")
            owner, repo = repo_parts[-2], repo_parts[-1].replace(".git", "")
            
            # Create PR
            pr_title = f"Decommission {database_name} database"
            pr_body = f"""
## Summary
This PR removes references to the `{database_name}` database as part of the decommissioning process.

## Changes Made
- Removed {len(changes_made)} database references
- Updated configuration files
- Updated documentation

## Files Modified
{chr(10).join(f"- {file}" for file in changes_made[:10])}
{"- ..." if len(changes_made) > 10 else ""}

## Testing
- [ ] Verify application still functions without database
- [ ] Run integration tests
- [ ] Validate configuration changes

🤖 Generated with [Claude Code](https://claude.ai/code)
"""
            
            pr_result = await github_client.create_pull_request(
                owner=owner,
                repo=repo,
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            result = {
                "pr_number": pr_result["number"],
                "pr_url": pr_result["html_url"],
                "title": pr_title
            }
            
            context.set_parameter("pr_url", pr_result["html_url"])
            
            self.logger.log_step_end("create_pull_request", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"PR creation failed", exception=e)
            self.logger.log_step_end("create_pull_request", {}, success=False)
            raise
    
    async def _notify_stakeholders(self, context: WorkflowContext) -> Dict[str, Any]:
        """Notify stakeholders about completion."""
        self.logger.log_step_start("notify_stakeholders", "Notifying stakeholders")
        
        try:
            slack_client = self._get_slack_client(context)
            database_name = context.get_parameter("database_name")
            pr_url = context.get_parameter("pr_url")
            changes_made = context.get_parameter("changes_made", [])
            
            # Send Slack notification
            message = f"""
🗄️ Database Decommissioning Complete

Database: `{database_name}`
Changes: {len(changes_made)} files modified
Pull Request: {pr_url}

Please review and merge the PR to complete the decommissioning process.
"""
            
            # Note: Channel ID would come from configuration
            channel_id = self.parameter_service.get_parameter("slack_channel_id", "general")
            
            notification_result = await slack_client.post_message(
                channel=channel_id,
                text=message
            )
            
            result = {
                "notification_sent": True,
                "channel": channel_id,
                "message_id": notification_result.get("ts")
            }
            
            self.logger.log_step_end("notify_stakeholders", result, success=True)
            return result
            
        except Exception as e:
            self.logger.log_error(f"Notification failed", exception=e)
            self.logger.log_step_end("notify_stakeholders", {}, success=False)
            # Don't fail workflow for notification issues
            return {"notification_sent": False, "error": str(e)}
    
    # Helper methods
    
    def _get_repomix_client(self, context: WorkflowContext) -> RepomixMCPClient:
        """Get or create Repomix client."""
        if "repomix_client" not in context._clients:
            context._clients["repomix_client"] = RepomixMCPClient(self.config_path)
        return context._clients["repomix_client"]
    
    def _get_github_client(self, context: WorkflowContext) -> GitHubMCPClient:
        """Get or create GitHub client."""
        if "github_client" not in context._clients:
            context._clients["github_client"] = GitHubMCPClient(self.config_path)
        return context._clients["github_client"]
    
    def _get_slack_client(self, context: WorkflowContext) -> SlackMCPClient:
        """Get or create Slack client."""
        if "slack_client" not in context._clients:
            context._clients["slack_client"] = SlackMCPClient(self.config_path)
        return context._clients["slack_client"]
    
    def _categorize_references(self, references: List[Dict]) -> List[Dict]:
        """Categorize database references by type."""
        categorized = []
        seen = set()
        
        for ref in references:
            key = f"{ref['file']}:{ref['line']}"
            if key in seen:
                continue
            seen.add(key)
            
            # Add category based on content analysis
            category = "unknown"
            content = ref.get("content", "").lower()
            
            if "config" in content or "setting" in content:
                category = "configuration"
            elif "import" in content or "from" in content:
                category = "import"
            elif "class" in content or "def" in content:
                category = "code_definition"
            elif "# " in content or "// " in content:
                category = "comment"
            else:
                category = "reference"
            
            categorized.append({
                **ref,
                "category": category
            })
        
        return categorized
    
    def _determine_strategy(self, file_path: str) -> str:
        """Determine processing strategy based on file type."""
        path = Path(file_path)
        
        if path.suffix in ['.tf', '.tfvars']:
            return 'infrastructure_files'
        elif path.suffix in ['.yml', '.yaml', '.json', '.toml']:
            return 'configuration_files'
        elif path.suffix in ['.py', '.js', '.ts', '.go', '.java', '.sh']:
            return 'code_files'
        elif path.suffix in ['.md', '.rst', '.txt']:
            return 'documentation_files'
        else:
            return 'code_files'  # Default to code
    
    def _get_strategy_priority(self, strategy: str) -> int:
        """Get processing priority for strategy."""
        priorities = {
            'configuration_files': 1,
            'infrastructure_files': 2,
            'code_files': 3,
            'documentation_files': 4
        }
        return priorities.get(strategy, 5)
    
    async def _process_action_item(self, github_client, owner, repo, branch, item):
        """Process individual action item."""
        # This would contain the actual file modification logic
        # For brevity, returning placeholder
        return item["files"]


# Example of simpler workflow pattern
class IncidentNotificationWorkflow:
    """Simple notification workflow for incident management."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = get_logger("incident_notification")
    
    async def execute(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute incident notification workflow."""
        try:
            # Build simple workflow
            workflow = (WorkflowBuilder("incident_notification", self.config_path)
                .step_auto("validate_incident", "Validate incident", self._validate_incident)
                .step_auto("send_slack_alert", "Send Slack alert", self._send_slack_alert)
                .step_auto("update_incident_status", "Update status", self._update_status)
                .build())
            
            return await workflow.execute(incident_data)
            
        except Exception as e:
            self.logger.log_error(f"Notification workflow failed", exception=e)
            return {"success": False, "error": str(e)}
    
    async def _validate_incident(self, context: WorkflowContext) -> Dict[str, Any]:
        """Validate incident data."""
        incident = context.get_parameter("incident")
        
        required_fields = ["id", "title", "severity"]
        for field in required_fields:
            if field not in incident:
                raise ValueError(f"Missing required field: {field}")
        
        return {"validated": True, "incident_id": incident["id"]}
    
    async def _send_slack_alert(self, context: WorkflowContext) -> Dict[str, Any]:
        """Send Slack alert for incident."""
        slack_client = SlackMCPClient(self.config_path)
        incident = context.get_parameter("incident")
        
        message = f"🚨 New Incident: {incident['title']} (Severity: {incident['severity']})"
        
        result = await slack_client.post_message(
            channel="incidents",
            text=message
        )
        
        return {"message_sent": True, "message_id": result.get("ts")}
    
    async def _update_status(self, context: WorkflowContext) -> Dict[str, Any]:
        """Update incident status."""
        # This would integrate with the incident database
        return {"status_updated": True}


# Usage examples
async def example_usage():
    """Example of how to use GraphMCP workflows in manager component."""
    
    # Database decommissioning workflow
    db_workflow = DatabaseDecommissionWorkflow("/path/to/mcp_config.json")
    result = await db_workflow.execute(
        database_name="legacy_reports_db",
        repository_url="https://github.com/company/app-repo"
    )
    
    # Incident notification workflow
    incident_workflow = IncidentNotificationWorkflow("/path/to/mcp_config.json")
    incident_result = await incident_workflow.execute({
        "incident": {
            "id": "INC-001",
            "title": "Database connection failure",
            "severity": "high",
            "description": "Unable to connect to primary database"
        }
    })
    
    return {
        "db_decommission": result,
        "incident_notification": incident_result
    }

if __name__ == "__main__":
    # Example execution
    asyncio.run(example_usage())