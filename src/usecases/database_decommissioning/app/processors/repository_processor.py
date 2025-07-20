"""
Repository Processor for Database Decommissioning.

This module provides repository processing functionality enhanced for Manager integration
while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced repository handling with Manager context
- Manager-specific logging and metrics
- Tenant-aware processing

GraphMCP Preservation:
- Repository processing step functionality
- MCP client integration patterns
- Workflow context management
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..utils import extract_repo_details, create_logger_for_workflow
from .pattern_discovery import PatternDiscoveryProcessor


class RepositoryProcessor:
    """
    Repository processor with Manager integration.
    
    Processes repositories for database decommissioning with enhanced Manager features.
    """

    def __init__(
        self,
        database_name: str,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Initialize repository processor.

        Args:
            database_name: Name of database being decommissioned
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"repo_processor_{int(time.time())}"

        # Initialize logger
        self.logger = create_logger_for_workflow(
            self.workflow_id, self.database_name, self.tenant_id
        )

    async def process_repositories(
        self,
        target_repos: List[str],
        slack_channel: Optional[str] = None,
        context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Process multiple repositories for database decommissioning.

        Args:
            target_repos: List of repository URLs to process
            slack_channel: Optional Slack channel for notifications
            context: Optional workflow context

        Returns:
            Dict containing repository processing results
        """
        start_time = time.time()

        self.logger.log_step_start(
            "repository_processing",
            f"Processing {len(target_repos)} repositories for database {self.database_name}",
            {
                "database_name": self.database_name,
                "target_repos": target_repos,
                "slack_channel": slack_channel,
                "tenant_id": self.tenant_id,
            },
        )

        try:
            # Initialize MCP clients if context provided
            github_client = None
            slack_client = None
            repomix_client = None

            if context:
                github_client = await self._initialize_github_client(context)
                slack_client = await self._initialize_slack_client(context)
                repomix_client = await self._initialize_repomix_client(context)

            # Process repositories concurrently
            processing_tasks = []
            for repo_url in target_repos:
                task = self._process_single_repository(
                    repo_url, github_client, repomix_client, context
                )
                processing_tasks.append(task)

            # Execute repository processing tasks
            repo_results = await asyncio.gather(*processing_tasks, return_exceptions=True)

            # Process results and handle exceptions
            processed_repositories = []
            failed_repositories = []
            total_files_processed = 0
            total_files_modified = 0

            for i, result in enumerate(repo_results):
                repo_url = target_repos[i]
                
                if isinstance(result, Exception):
                    self.logger.log_error(f"Repository processing failed for {repo_url}", result)
                    failed_repositories.append({
                        "repo_url": repo_url,
                        "error": str(result),
                    })
                else:
                    processed_repositories.append(result)
                    total_files_processed += result.get("total_files_processed", 0)
                    total_files_modified += result.get("total_files_modified", 0)

            # Send Slack notification if configured
            if slack_client and slack_channel:
                await self._send_processing_notification(
                    slack_client, slack_channel, processed_repositories, failed_repositories
                )

            # Create comprehensive result
            processing_result = {
                "database_name": self.database_name,
                "tenant_id": self.tenant_id,
                "repositories_processed": len(processed_repositories),
                "repositories_failed": len(failed_repositories),
                "total_repositories": len(target_repos),
                "total_files_processed": total_files_processed,
                "total_files_modified": total_files_modified,
                "processed_repositories": processed_repositories,
                "failed_repositories": failed_repositories,
                "success": len(failed_repositories) == 0,
                "duration": time.time() - start_time,
            }

            # Log processing summary
            self._log_repository_processing_summary(processing_result)

            self.logger.log_step_end("repository_processing", processing_result, success=processing_result["success"])

            return processing_result

        except Exception as e:
            self.logger.log_error("Repository processing failed", e)
            raise

    async def _process_single_repository(
        self,
        repo_url: str,
        github_client: Any,
        repomix_client: Any,
        context: Optional[Any],
    ) -> Dict[str, Any]:
        """Process a single repository."""
        repo_start_time = time.time()
        
        # Extract repository details
        repo_owner, repo_name = extract_repo_details(repo_url)
        
        self.logger.log_info(f"Processing repository: {repo_owner}/{repo_name}")

        try:
            # Get repository content using repomix
            repo_content = await self._get_repository_content(
                repomix_client, repo_url, repo_owner, repo_name
            )

            # Perform pattern discovery
            pattern_processor = PatternDiscoveryProcessor(
                self.database_name, repo_owner, repo_name, self.tenant_id, self.workflow_id
            )
            
            discovery_result = await pattern_processor.discover_patterns_in_repository(repo_content)

            # Calculate repository metrics
            total_files = discovery_result.get("total_files", 0)
            matched_files = discovery_result.get("matched_files", 0)
            files_by_type = discovery_result.get("files_by_type", {})

            result = {
                "repo_url": repo_url,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "total_files_processed": total_files,
                "total_files_modified": matched_files,
                "files_by_type": files_by_type,
                "discovery_result": discovery_result,
                "success": True,
                "duration": time.time() - repo_start_time,
            }

            # Store discovery result in context if available
            if context:
                context.set_shared_value(f"discovery_{repo_owner}_{repo_name}", discovery_result)

            return result

        except Exception as e:
            self.logger.log_error(f"Failed to process repository {repo_owner}/{repo_name}", e)
            return {
                "repo_url": repo_url,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "total_files_processed": 0,
                "total_files_modified": 0,
                "files_by_type": {},
                "discovery_result": {},
                "success": False,
                "error": str(e),
                "duration": time.time() - repo_start_time,
            }

    async def _get_repository_content(
        self,
        repomix_client: Any,
        repo_url: str,
        repo_owner: str,
        repo_name: str,
    ) -> Dict[str, Any]:
        """Get repository content using repomix."""
        try:
            if not repomix_client:
                # Fallback to mock content if repomix not available
                self.logger.log_warning(f"Repomix client not available for {repo_owner}/{repo_name}, using mock content")
                return {
                    "files": [],
                    "content": "",
                    "repository": f"{repo_owner}/{repo_name}",
                    "mock": True,
                }

            # Use repomix to get repository content
            pack_result = await repomix_client.pack_remote_repository(repo_url)
            
            if pack_result.get("success"):
                content = await repomix_client.read_repomix_output(pack_result["output_id"])
                return {
                    "files": self._parse_repomix_content(content),
                    "content": content,
                    "repository": f"{repo_owner}/{repo_name}",
                    "pack_result": pack_result,
                }
            else:
                raise Exception(f"Repomix pack failed: {pack_result.get('error', 'Unknown error')}")

        except Exception as e:
            self.logger.log_error(f"Failed to get repository content for {repo_owner}/{repo_name}", e)
            # Return empty content structure
            return {
                "files": [],
                "content": "",
                "repository": f"{repo_owner}/{repo_name}",
                "error": str(e),
            }

    def _parse_repomix_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse repomix content into file structures."""
        files = []
        current_file = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## File: '):
                # Save previous file
                if current_file:
                    files.append({
                        "path": current_file,
                        "content": '\n'.join(current_content),
                    })
                
                # Start new file
                current_file = line.replace('## File: ', '').strip()
                current_content = []
            elif current_file:
                current_content.append(line)

        # Save last file
        if current_file:
            files.append({
                "path": current_file,
                "content": '\n'.join(current_content),
            })

        return files

    async def _initialize_github_client(self, context: Any) -> Any:
        """Initialize GitHub MCP client."""
        try:
            if hasattr(context, 'clients') and 'ovr_github' in context.clients:
                return context.clients['ovr_github']
            
            # Try to initialize GitHub client
            from src.frameworks.graphmcp.clients.github import GitHubMCPClient
            github_client = GitHubMCPClient(context.config.config_path)
            
            # Store in context for reuse
            if hasattr(context, 'clients'):
                context.clients['ovr_github'] = github_client
            
            return github_client

        except Exception as e:
            self.logger.log_warning(f"Failed to initialize GitHub client: {e}")
            return None

    async def _initialize_slack_client(self, context: Any) -> Any:
        """Initialize Slack MCP client."""
        try:
            if hasattr(context, 'clients') and 'ovr_slack' in context.clients:
                return context.clients['ovr_slack']
            
            # Try to initialize Slack client
            from src.frameworks.graphmcp.clients.slack import SlackMCPClient
            slack_client = SlackMCPClient(context.config.config_path)
            
            # Store in context for reuse
            if hasattr(context, 'clients'):
                context.clients['ovr_slack'] = slack_client
            
            return slack_client

        except Exception as e:
            self.logger.log_warning(f"Failed to initialize Slack client: {e}")
            return None

    async def _initialize_repomix_client(self, context: Any) -> Any:
        """Initialize Repomix MCP client."""
        try:
            if hasattr(context, 'clients') and 'ovr_repomix' in context.clients:
                return context.clients['ovr_repomix']
            
            # Try to initialize Repomix client
            from src.frameworks.graphmcp.clients.repomix import RepomixMCPClient
            repomix_client = RepomixMCPClient(context.config.config_path)
            
            # Store in context for reuse
            if hasattr(context, 'clients'):
                context.clients['ovr_repomix'] = repomix_client
            
            return repomix_client

        except Exception as e:
            self.logger.log_warning(f"Failed to initialize Repomix client: {e}")
            return None

    async def _send_processing_notification(
        self,
        slack_client: Any,
        slack_channel: str,
        processed_repositories: List[Dict[str, Any]],
        failed_repositories: List[Dict[str, Any]],
    ):
        """Send processing notification to Slack."""
        try:
            total_repos = len(processed_repositories) + len(failed_repositories)
            success_count = len(processed_repositories)
            
            message = f"""
🔍 **Database Decommissioning - Repository Processing Complete**

**Database:** {self.database_name}
**Total Repositories:** {total_repos}
**Successfully Processed:** {success_count}
**Failed:** {len(failed_repositories)}

**Processed Repositories:**
"""
            
            for repo in processed_repositories[:5]:  # Limit to first 5
                files_processed = repo.get("total_files_processed", 0)
                files_modified = repo.get("total_files_modified", 0)
                message += f"• {repo['repo_owner']}/{repo['repo_name']}: {files_modified}/{files_processed} files affected\n"
            
            if len(processed_repositories) > 5:
                message += f"• ... and {len(processed_repositories) - 5} more repositories\n"

            if failed_repositories:
                message += f"\n**Failed Repositories:**\n"
                for repo in failed_repositories[:3]:  # Limit to first 3
                    message += f"• {repo['repo_url']}: {repo['error']}\n"

            # Send notification
            await slack_client.post_message(slack_channel, message)

        except Exception as e:
            self.logger.log_error("Failed to send Slack notification", e)

    def _log_repository_processing_summary(self, result: Dict[str, Any]):
        """Log repository processing summary with structured data."""
        # Log summary metrics
        summary_table = [
            {"metric": "Total Repositories", "value": str(result["total_repositories"])},
            {"metric": "Successfully Processed", "value": str(result["repositories_processed"])},
            {"metric": "Failed", "value": str(result["repositories_failed"])},
            {"metric": "Total Files Processed", "value": str(result["total_files_processed"])},
            {"metric": "Total Files Modified", "value": str(result["total_files_modified"])},
            {"metric": "Duration", "value": f"{result['duration']:.1f}s"},
        ]
        
        self.logger.log_table("Repository Processing Summary", summary_table)

        # Log individual repository results
        if result["processed_repositories"]:
            repo_table = []
            for repo in result["processed_repositories"]:
                repo_table.append({
                    "repository": f"{repo['repo_owner']}/{repo['repo_name']}",
                    "files_processed": str(repo["total_files_processed"]),
                    "files_modified": str(repo["total_files_modified"]),
                    "duration": f"{repo['duration']:.1f}s",
                    "status": "✅" if repo["success"] else "❌",
                })
            
            self.logger.log_table("Repository Processing Details", repo_table)

        # Log failed repositories if any
        if result["failed_repositories"]:
            failed_table = []
            for repo in result["failed_repositories"]:
                failed_table.append({
                    "repository": repo["repo_url"],
                    "error": repo["error"][:100] + "..." if len(repo["error"]) > 100 else repo["error"],
                })
            
            self.logger.log_table("Failed Repository Processing", failed_table)


# Legacy compatibility functions for GraphMCP integration
async def process_repositories_step(
    context: Any,
    step: Any,
    database_name: str = "example_database",
    target_repos: Optional[List[str]] = None,
    slack_channel: str = "demo-channel",
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Legacy compatibility function for GraphMCP workflow integration.

    Args:
        context: WorkflowContext for data sharing
        step: Step configuration object
        database_name: Name of the database to decommission
        target_repos: List of repository URLs to process
        slack_channel: Slack channel for notifications
        workflow_id: Unique workflow identifier

    Returns:
        Dict containing repository processing results
    """
    if not target_repos:
        target_repos = ["https://github.com/bprzybys-nc/postgres-sample-dbs"]

    processor = RepositoryProcessor(database_name, workflow_id=workflow_id)
    result = await processor.process_repositories(target_repos, slack_channel, context)

    # Store results in context for other steps (GraphMCP compatibility)
    context.set_shared_value("repository_processing", result)
    
    # Store discovery results for the primary repository
    if result["processed_repositories"]:
        primary_repo = result["processed_repositories"][0]
        context.set_shared_value("discovery", primary_repo.get("discovery_result", {}))

    return result


async def initialize_github_client(context: Any, logger: Any) -> Any:
    """Legacy compatibility function for initializing GitHub client."""
    processor = RepositoryProcessor("legacy_db")
    return await processor._initialize_github_client(context)


async def initialize_slack_client(context: Any, logger: Any) -> Any:
    """Legacy compatibility function for initializing Slack client."""
    processor = RepositoryProcessor("legacy_db")
    return await processor._initialize_slack_client(context)


async def initialize_repomix_client(context: Any, logger: Any) -> Any:
    """Legacy compatibility function for initializing Repomix client."""
    processor = RepositoryProcessor("legacy_db")
    return await processor._initialize_repomix_client(context)


async def send_slack_notification_with_retry(
    slack_client: Any,
    channel: str,
    message: str,
    max_retries: int = 3,
    logger: Optional[Any] = None,
) -> bool:
    """Legacy compatibility function for sending Slack notifications with retry."""
    for attempt in range(max_retries):
        try:
            await slack_client.post_message(channel, message)
            return True
        except Exception as e:
            if logger:
                logger.log_warning(f"Slack notification attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return False