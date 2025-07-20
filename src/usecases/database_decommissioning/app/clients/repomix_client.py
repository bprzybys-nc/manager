"""
Repomix MCP Client Wrapper for Database Decommissioning.

This module provides a Manager-integrated wrapper for the Repomix MCP client,
enabling enhanced repository packaging and analysis for database decommissioning workflows.

Manager Integration:
- Enhanced repository packaging with Manager context
- Tenant-aware repository processing
- Graceful degradation for Repomix limitations
- Manager-specific logging and error handling

GraphMCP Preservation:
- Full RepomixMCPClient compatibility
- Standard Repomix MCP tool support
- Repository packaging and analysis patterns
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.clients.repomix import RepomixMCPClient
from src.frameworks.graphmcp.clients.base import MCPToolError

# Local imports
from .base import BaseMCPClientWrapper
from ..utils import extract_repo_details


class RepomixClientWrapper(BaseMCPClientWrapper):
    """
    Repomix MCP client wrapper with Manager integration.
    
    Provides enhanced repository packaging and analysis for database decommissioning
    workflows while maintaining full GraphMCP framework compatibility.
    """

    @property
    def client_class(self) -> type:
        """Return the GraphMCP Repomix client class."""
        return RepomixMCPClient

    @property
    def server_name(self) -> str:
        """Return the MCP server name for Repomix client."""
        return "ovr_repomix"

    async def pack_remote_repository(
        self,
        repo_url: str,
        output_file: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Pack remote repository with Manager enhancements.

        Args:
            repo_url: GitHub repository URL to pack
            output_file: Optional output file path
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            branch: Specific branch to pack (defaults to default branch)

        Returns:
            Enhanced repository packing result with Manager metadata
        """
        try:
            owner, repo = extract_repo_details(repo_url)
            
            self.logger.log_info(
                f"Packing remote repository: {owner}/{repo}",
                {
                    "repo_url": repo_url,
                    "branch": branch,
                    "include_patterns": len(include_patterns or []),
                    "exclude_patterns": len(exclude_patterns or []),
                }
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "pack_remote_repository",
                    Exception("Repomix client not available"),
                    {
                        "repository_url": repo_url,
                        "output_file": output_file,
                        "files_packed": 0,
                        "total_size": 0,
                        "packing_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.pack_remote_repository(
                repo_url, output_file, include_patterns, exclude_patterns, branch
            )

            # Enhance result with Manager metadata
            enhanced_result = self._create_enhanced_result(
                result,
                "pack_remote_repository",
                repository_url=repo_url,
                owner=owner,
                repo=repo,
                branch=branch,
                database_context=True,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully packed repository: {owner}/{repo}",
                    {
                        "files_packed": result.get("files_packed", 0),
                        "total_size": result.get("total_size", 0),
                        "output_file": result.get("output_file"),
                    }
                )
            else:
                self.logger.log_warning(
                    f"Repository packing failed: {owner}/{repo}",
                    {"error": result.get("error")}
                )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to pack remote repository: {repo_url}", e)
            return self._handle_graceful_degradation(
                "pack_remote_repository",
                e,
                {
                    "repository_url": repo_url,
                    "output_file": output_file,
                    "files_packed": 0,
                    "total_size": 0,
                    "packing_failed": True,
                }
            )

    async def pack_codebase(
        self,
        directory_path: str,
        output_file: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Pack local codebase with Manager enhancements.

        Args:
            directory_path: Local directory path to pack
            output_file: Optional output file path
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude

        Returns:
            Enhanced codebase packing result with Manager metadata
        """
        try:
            self.logger.log_info(
                f"Packing local codebase: {directory_path}",
                {
                    "directory": directory_path,
                    "include_patterns": len(include_patterns or []),
                    "exclude_patterns": len(exclude_patterns or []),
                }
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "pack_codebase",
                    Exception("Repomix client not available"),
                    {
                        "directory_path": directory_path,
                        "output_file": output_file,
                        "files_packed": 0,
                        "total_size": 0,
                        "packing_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.pack_codebase(
                directory_path, output_file, include_patterns, exclude_patterns
            )

            enhanced_result = self._create_enhanced_result(
                result,
                "pack_codebase",
                directory_path=directory_path,
                database_context=True,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully packed codebase: {directory_path}",
                    {
                        "files_packed": result.get("files_packed", 0),
                        "total_size": result.get("total_size", 0),
                        "output_file": result.get("output_file"),
                    }
                )
            else:
                self.logger.log_warning(
                    f"Codebase packing failed: {directory_path}",
                    {"error": result.get("error")}
                )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to pack codebase: {directory_path}", e)
            return self._handle_graceful_degradation(
                "pack_codebase",
                e,
                {
                    "directory_path": directory_path,
                    "output_file": output_file,
                    "files_packed": 0,
                    "total_size": 0,
                    "packing_failed": True,
                }
            )

    async def grep_repomix_output(
        self,
        output_file: str,
        pattern: str,
        context_lines: int = 2,
        case_sensitive: bool = True,
        max_matches: int = 100,
    ) -> Dict[str, Any]:
        """
        Search patterns in repomix output with Manager enhancements.

        Args:
            output_file: Path to repomix output file
            pattern: Regex pattern to search for
            context_lines: Number of context lines around matches
            case_sensitive: Whether search should be case sensitive
            max_matches: Maximum number of matches to return

        Returns:
            Enhanced search results with Manager metadata
        """
        try:
            self.logger.log_info(
                f"Searching repomix output: {output_file}",
                {
                    "pattern": pattern,
                    "context_lines": context_lines,
                    "case_sensitive": case_sensitive,
                    "max_matches": max_matches,
                }
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "grep_repomix_output",
                    Exception("Repomix client not available"),
                    {
                        "output_file": output_file,
                        "pattern": pattern,
                        "total_matches": 0,
                        "matches": [],
                        "search_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.grep_repomix_output(
                output_file, pattern, context_lines, case_sensitive, max_matches
            )

            enhanced_result = self._create_enhanced_result(
                result,
                "grep_repomix_output",
                output_file=output_file,
                pattern=pattern,
                database_search=True,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Search completed in {output_file}",
                    {
                        "pattern": pattern,
                        "total_matches": result.get("total_matches", 0),
                        "files_searched": result.get("files_searched", 0),
                    }
                )
            else:
                self.logger.log_warning(
                    f"Search failed in {output_file}",
                    {"pattern": pattern, "error": result.get("error")}
                )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to grep repomix output: {output_file}", e)
            return self._handle_graceful_degradation(
                "grep_repomix_output",
                e,
                {
                    "output_file": output_file,
                    "pattern": pattern,
                    "total_matches": 0,
                    "matches": [],
                    "search_failed": True,
                }
            )

    async def read_repomix_output(
        self,
        output_id: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Read repomix output content with Manager enhancements.

        Args:
            output_id: ID of the repomix output file
            start_line: Starting line number (1-based, inclusive)
            end_line: Ending line number (1-based, inclusive)

        Returns:
            Enhanced file content with Manager metadata
        """
        try:
            self.logger.log_info(
                f"Reading repomix output: {output_id}",
                {"start_line": start_line, "end_line": end_line}
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "read_repomix_output",
                    Exception("Repomix client not available"),
                    {
                        "output_id": output_id,
                        "content": "",
                        "lines_read": 0,
                        "read_skipped": True,
                    }
                )

            # Use call_tool_with_retry for reading
            params = {"outputId": output_id}
            if start_line is not None:
                params["startLine"] = start_line
            if end_line is not None:
                params["endLine"] = end_line

            result = await self.call_tool_with_retry("read_repomix_output", params)

            # Create enhanced result
            content = result.get("content", "")
            lines_read = len(content.split("\n")) if content else 0

            enhanced_result = self._create_enhanced_result(
                {
                    "success": True,
                    "output_id": output_id,
                    "content": content,
                    "lines_read": lines_read,
                    "start_line": start_line,
                    "end_line": end_line,
                },
                "read_repomix_output",
                output_id=output_id,
                content_length=len(content),
            )

            self.logger.log_info(
                f"Successfully read repomix output: {output_id}",
                {"lines_read": lines_read, "content_length": len(content)}
            )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to read repomix output: {output_id}", e)
            return self._handle_graceful_degradation(
                "read_repomix_output",
                e,
                {
                    "output_id": output_id,
                    "content": "",
                    "lines_read": 0,
                    "read_failed": True,
                }
            )

    async def analyze_repository_for_database(
        self,
        repo_url: str,
        database_name: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze repository specifically for database references.

        Args:
            repo_url: Repository URL to analyze
            database_name: Database name to search for
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude

        Returns:
            Database-specific repository analysis
        """
        try:
            self.logger.log_info(
                f"Analyzing repository for database '{database_name}': {repo_url}"
            )

            # First, pack the repository
            pack_result = await self.pack_remote_repository(
                repo_url, include_patterns=include_patterns, exclude_patterns=exclude_patterns
            )

            if not pack_result.get("success"):
                return self._create_enhanced_result(
                    {
                        "success": False,
                        "repository_url": repo_url,
                        "database_name": database_name,
                        "error": "Failed to pack repository",
                        "pack_result": pack_result,
                    },
                    "analyze_repository_for_database",
                )

            output_file = pack_result.get("output_file")
            if not output_file:
                return self._create_enhanced_result(
                    {
                        "success": False,
                        "repository_url": repo_url,
                        "database_name": database_name,
                        "error": "No output file from repository packing",
                    },
                    "analyze_repository_for_database",
                )

            # Search for database references
            search_patterns = [
                f"\\b{database_name}\\b",
                f"'{database_name}'",
                f'"{database_name}"',
                f"{database_name}\\.",
            ]

            search_results = []
            total_matches = 0

            for pattern in search_patterns:
                search_result = await self.grep_repomix_output(
                    output_file, pattern, context_lines=3, case_sensitive=False, max_matches=50
                )
                
                if search_result.get("success"):
                    matches = search_result.get("matches", [])
                    if matches:
                        search_results.append({
                            "pattern": pattern,
                            "matches": matches,
                            "match_count": len(matches),
                        })
                        total_matches += len(matches)

            # Create comprehensive analysis result
            analysis_result = {
                "success": True,
                "repository_url": repo_url,
                "database_name": database_name,
                "pack_result": pack_result,
                "search_patterns": search_patterns,
                "search_results": search_results,
                "total_matches": total_matches,
                "files_packed": pack_result.get("files_packed", 0),
                "total_size": pack_result.get("total_size", 0),
                "output_file": output_file,
            }

            enhanced_result = self._create_enhanced_result(
                analysis_result,
                "analyze_repository_for_database",
                database_name=database_name,
                total_matches=total_matches,
                analysis_type="database_search",
            )

            self.logger.log_info(
                f"Database analysis completed for {repo_url}",
                {
                    "database_name": database_name,
                    "total_matches": total_matches,
                    "files_packed": pack_result.get("files_packed", 0),
                }
            )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(
                f"Failed to analyze repository for database '{database_name}': {repo_url}", e
            )
            return self._handle_graceful_degradation(
                "analyze_repository_for_database",
                e,
                {
                    "repository_url": repo_url,
                    "database_name": database_name,
                    "total_matches": 0,
                    "analysis_failed": True,
                }
            )


# Legacy compatibility functions for GraphMCP integration
async def create_repomix_client(
    config_path: str | Path,
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> RepomixClientWrapper:
    """
    Factory function to create Repomix client wrapper.

    Args:
        config_path: Path to MCP configuration file
        tenant_id: Optional tenant identifier
        workflow_id: Optional workflow identifier

    Returns:
        Initialized Repomix client wrapper
    """
    return RepomixClientWrapper(config_path, tenant_id, workflow_id)


async def pack_repository_with_fallback(
    repomix_client: RepomixClientWrapper,
    repo_url: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Pack repository with graceful fallback.

    Args:
        repomix_client: Repomix client wrapper instance
        repo_url: Repository URL to pack
        **kwargs: Additional packing parameters

    Returns:
        Repository packing result with fallback handling
    """
    try:
        return await repomix_client.pack_remote_repository(repo_url, **kwargs)
    except Exception as e:
        return {
            "success": False,
            "repository_url": repo_url,
            "fallback_mode": True,
            "error": str(e),
            "files_packed": 0,
            "total_size": 0,
        }


async def search_database_references(
    repomix_client: RepomixClientWrapper,
    output_file: str,
    database_name: str,
) -> Dict[str, Any]:
    """
    Search for database references in repomix output.

    Args:
        repomix_client: Repomix client wrapper instance
        output_file: Repomix output file path
        database_name: Database name to search for

    Returns:
        Database reference search results
    """
    try:
        # Create search pattern for database name
        pattern = f"\\b{database_name}\\b"
        
        return await repomix_client.grep_repomix_output(
            output_file, pattern, context_lines=2, case_sensitive=False, max_matches=100
        )
    except Exception as e:
        return {
            "success": False,
            "output_file": output_file,
            "pattern": pattern,
            "total_matches": 0,
            "matches": [],
            "error": str(e),
        }