"""
GitHub MCP Client Wrapper for Database Decommissioning.

This module provides a Manager-integrated wrapper for the GitHub MCP client,
enabling enhanced GitHub operations for database decommissioning workflows.

Manager Integration:
- Enhanced repository analysis with Manager context
- Manager-specific logging and error handling
- Tenant-aware GitHub operations
- Graceful degradation for GitHub API limitations

GraphMCP Preservation:
- Full GitHubMCPClient compatibility
- Standard GitHub MCP tool support
- Repository management patterns
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.clients.github import GitHubMCPClient
from src.frameworks.graphmcp.clients.base import MCPToolError

# Local imports
from .base import BaseMCPClientWrapper
from ..utils import extract_repo_details


class GitHubClientWrapper(BaseMCPClientWrapper):
    """
    GitHub MCP client wrapper with Manager integration.
    
    Provides enhanced GitHub operations for database decommissioning workflows
    while maintaining full GraphMCP framework compatibility.
    """

    @property
    def client_class(self) -> type:
        """Return the GraphMCP GitHub client class."""
        return GitHubMCPClient

    @property
    def server_name(self) -> str:
        """Return the MCP server name for GitHub client."""
        return "ovr_github"

    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """
        Get comprehensive repository information with Manager enhancements.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Enhanced repository information with Manager metadata
        """
        try:
            # Extract owner and repo from URL
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(f"Getting repository info for {owner}/{repo}")

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "get_repository_info",
                    Exception("GitHub client not available"),
                    {
                        "owner": owner,
                        "repo": repo,
                        "repository_url": repo_url,
                        "basic_info_only": True,
                    }
                )

            client = await self._initialize_client()
            repo_info = await client.get_repository(owner, repo)

            # Enhance with Manager metadata
            enhanced_info = self._create_enhanced_result(
                repo_info,
                "get_repository_info",
                repository_url=repo_url,
                owner=owner,
                repo=repo,
            )

            self.logger.log_info(f"Retrieved repository info for {owner}/{repo}")
            return enhanced_info

        except Exception as e:
            self.logger.log_error(f"Failed to get repository info for {repo_url}", e)
            owner, repo = extract_repo_details(repo_url)  # Get fallback values
            return self._handle_graceful_degradation(
                "get_repository_info",
                e,
                {
                    "owner": owner,
                    "repo": repo,
                    "repository_url": repo_url,
                    "error_occurred": True,
                }
            )

    async def analyze_repository_structure(self, repo_url: str) -> Dict[str, Any]:
        """
        Analyze repository structure with enhanced Manager features.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Comprehensive repository structure analysis
        """
        try:
            self.logger.log_info(f"Analyzing repository structure: {repo_url}")

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "analyze_repository_structure",
                    Exception("GitHub client not available"),
                    {
                        "repository_url": repo_url,
                        "analysis_limited": True,
                        "structure": {},
                    }
                )

            client = await self._initialize_client()
            structure = await client.analyze_repo_structure(repo_url)

            # Enhance analysis with Manager context
            enhanced_structure = self._create_enhanced_result(
                structure,
                "analyze_repository_structure",
                analysis_type="database_decommissioning",
                repo_url=repo_url,
            )

            self.logger.log_info(
                f"Repository structure analysis complete: {repo_url}",
                {"file_count": structure.get("file_count", 0)}
            )
            
            return enhanced_structure

        except Exception as e:
            self.logger.log_error(f"Failed to analyze repository structure: {repo_url}", e)
            return self._handle_graceful_degradation(
                "analyze_repository_structure",
                e,
                {
                    "repository_url": repo_url,
                    "analysis_failed": True,
                    "structure": {},
                }
            )

    async def get_file_content(
        self,
        repo_url: str,
        file_path: str,
        ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get file content from repository with Manager enhancements.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to file in repository
            ref: Git reference (branch, tag, commit)

        Returns:
            File content with Manager metadata
        """
        try:
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(f"Getting file content: {owner}/{repo}/{file_path}")

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "get_file_content",
                    Exception("GitHub client not available"),
                    {
                        "repository_url": repo_url,
                        "file_path": file_path,
                        "content": "",
                        "content_unavailable": True,
                    }
                )

            client = await self._initialize_client()
            content = await client.get_file_contents(owner, repo, file_path, ref)

            result = {
                "success": True,
                "repository_url": repo_url,
                "file_path": file_path,
                "content": content,
                "ref": ref,
                "content_length": len(content),
            }

            enhanced_result = self._create_enhanced_result(
                result,
                "get_file_content",
                owner=owner,
                repo=repo,
                file_path=file_path,
            )

            self.logger.log_info(f"Retrieved file content: {file_path} ({len(content)} chars)")
            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to get file content: {file_path}", e)
            return self._handle_graceful_degradation(
                "get_file_content",
                e,
                {
                    "repository_url": repo_url,
                    "file_path": file_path,
                    "content": "",
                    "content_failed": True,
                }
            )

    async def update_file_content(
        self,
        repo_url: str,
        file_path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update file content in repository with Manager tracking.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to file in repository
            content: New file content
            message: Commit message
            branch: Target branch (optional)
            sha: Current file SHA for updates (optional)

        Returns:
            File update result with Manager metadata
        """
        try:
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(
                f"Updating file content: {owner}/{repo}/{file_path}",
                {"content_length": len(content), "branch": branch}
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "update_file_content",
                    Exception("GitHub client not available"),
                    {
                        "repository_url": repo_url,
                        "file_path": file_path,
                        "update_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.create_or_update_file(
                owner, repo, file_path, content, message, branch, sha
            )

            enhanced_result = self._create_enhanced_result(
                result,
                "update_file_content",
                repository_url=repo_url,
                content_length=len(content),
                commit_message=message,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully updated file: {file_path}",
                    {"commit_sha": result.get("commit_sha")}
                )
            else:
                self.logger.log_warning(f"File update failed: {file_path}")

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to update file content: {file_path}", e)
            return self._handle_graceful_degradation(
                "update_file_content",
                e,
                {
                    "repository_url": repo_url,
                    "file_path": file_path,
                    "update_failed": True,
                }
            )

    async def search_code(
        self,
        query: str,
        sort: str = "indexed",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for code across repositories with Manager enhancements.

        Args:
            query: Search query string
            sort: Sort field (indexed, created, updated)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            Enhanced search results with Manager metadata
        """
        try:
            self.logger.log_info(f"Searching code: {query}")

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "search_code",
                    Exception("GitHub client not available"),
                    {
                        "query": query,
                        "total_count": 0,
                        "items": [],
                        "search_unavailable": True,
                    }
                )

            client = await self._initialize_client()
            search_result = await client.search_code(query, sort, order, per_page, page)

            enhanced_result = self._create_enhanced_result(
                search_result,
                "search_code",
                query=query,
                page=page,
                per_page=per_page,
            )

            self.logger.log_info(
                f"Code search completed: {search_result.get('total_count', 0)} results",
                {"query": query, "items_returned": len(search_result.get("items", []))}
            )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to search code: {query}", e)
            return self._handle_graceful_degradation(
                "search_code",
                e,
                {
                    "query": query,
                    "total_count": 0,
                    "items": [],
                    "search_failed": True,
                }
            )

    async def create_issue(
        self,
        repo_url: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create issue in repository with Manager tracking.

        Args:
            repo_url: GitHub repository URL
            title: Issue title
            body: Issue description
            labels: Issue labels
            assignees: Issue assignees

        Returns:
            Issue creation result with Manager metadata
        """
        try:
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(f"Creating issue in {owner}/{repo}: {title}")

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "create_issue",
                    Exception("GitHub client not available"),
                    {
                        "repository_url": repo_url,
                        "title": title,
                        "issue_creation_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.create_issue(owner, repo, title, body, labels, assignees)

            enhanced_result = self._create_enhanced_result(
                result,
                "create_issue",
                repository_url=repo_url,
                title=title,
                labels=labels or [],
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully created issue #{result.get('number')}: {title}"
                )
            else:
                self.logger.log_warning(f"Issue creation failed: {title}")

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to create issue: {title}", e)
            return self._handle_graceful_degradation(
                "create_issue",
                e,
                {
                    "repository_url": repo_url,
                    "title": title,
                    "issue_creation_failed": True,
                }
            )

    async def create_pull_request(
        self,
        repo_url: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Create pull request with Manager tracking.

        Args:
            repo_url: GitHub repository URL
            title: Pull request title
            head: Branch containing changes
            base: Target branch for merge
            body: Pull request description
            draft: Whether to create as draft PR

        Returns:
            Pull request creation result with Manager metadata
        """
        try:
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(
                f"Creating pull request in {owner}/{repo}: {title}",
                {"head": head, "base": base, "draft": draft}
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "create_pull_request",
                    Exception("GitHub client not available"),
                    {
                        "repository_url": repo_url,
                        "title": title,
                        "head": head,
                        "base": base,
                        "pr_creation_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.create_pull_request(
                owner, repo, title, head, base, body, draft
            )

            enhanced_result = self._create_enhanced_result(
                result,
                "create_pull_request",
                repository_url=repo_url,
                title=title,
                head=head,
                base=base,
                draft=draft,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully created PR #{result.get('number')}: {title}",
                    {"url": result.get("url")}
                )
            else:
                self.logger.log_warning(f"Pull request creation failed: {title}")

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to create pull request: {title}", e)
            return self._handle_graceful_degradation(
                "create_pull_request",
                e,
                {
                    "repository_url": repo_url,
                    "title": title,
                    "head": head,
                    "base": base,
                    "pr_creation_failed": True,
                }
            )


# Legacy compatibility functions for GraphMCP integration
async def create_github_client(
    config_path: str | Path,
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> GitHubClientWrapper:
    """
    Factory function to create GitHub client wrapper.

    Args:
        config_path: Path to MCP configuration file
        tenant_id: Optional tenant identifier
        workflow_id: Optional workflow identifier

    Returns:
        Initialized GitHub client wrapper
    """
    return GitHubClientWrapper(config_path, tenant_id, workflow_id)


async def get_repository_info_with_fallback(
    github_client: GitHubClientWrapper, repo_url: str
) -> Dict[str, Any]:
    """
    Get repository information with graceful fallback.

    Args:
        github_client: GitHub client wrapper instance
        repo_url: Repository URL

    Returns:
        Repository information with fallback data if needed
    """
    try:
        return await github_client.get_repository_info(repo_url)
    except Exception as e:
        owner, repo = extract_repo_details(repo_url)
        return {
            "repository_url": repo_url,
            "owner": owner,
            "repo": repo,
            "fallback_mode": True,
            "error": str(e),
        }