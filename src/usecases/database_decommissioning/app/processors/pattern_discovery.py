"""
Pattern Discovery Processor for Database Decommissioning.

This module provides pattern discovery and file processing functionality enhanced for Manager integration
while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced AI processing with Manager's Azure OpenAI
- Manager-specific logging and metrics
- Tenant context and processing

GraphMCP Preservation:
- AgenticFileProcessor functionality
- Source type classification patterns
- Batch processing logic
"""

import json
import os
import time
from typing import Any, Dict, List, Optional
from collections import defaultdict

# Manager imports
import src.config as manager_config

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.utils.source_type_classifier import SourceType, SourceTypeClassifier
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..models import FileProcessingResult


class PatternDiscoveryProcessor:
    """
    Pattern discovery processor with Manager integration.
    
    Provides AI-powered pattern discovery and file processing capabilities.
    """

    def __init__(
        self,
        database_name: str,
        repo_owner: str,
        repo_name: str,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Initialize pattern discovery processor.

        Args:
            database_name: Name of database being decommissioned
            repo_owner: Repository owner name
            repo_name: Repository name
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"pattern_discovery_{int(time.time())}"

        # Initialize components
        self.source_classifier = SourceTypeClassifier()
        
        # Initialize Azure OpenAI client with Manager configuration
        self.ai_client = self._initialize_ai_client()
        
        # Initialize logger
        config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id=self.workflow_id, config=config)

    def _initialize_ai_client(self):
        """Initialize Azure OpenAI client using Manager configuration."""
        try:
            # Use Manager's Azure OpenAI configuration
            api_key = getattr(manager_config, 'AZURE_OPENAI_API_KEY', None)
            endpoint = getattr(manager_config, 'AZURE_OPENAI_ENDPOINT', None)

            if not api_key:
                self.logger.log_warning("Azure OpenAI API key not configured in Manager")
                return None

            # Import and configure Azure OpenAI client
            from openai import AsyncAzureOpenAI
            
            client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version="2024-02-15-preview"
            )
            
            self.logger.log_info("Azure OpenAI client initialized successfully")
            return client

        except Exception as e:
            self.logger.log_error("Failed to initialize Azure OpenAI client", e)
            return None

    async def discover_patterns_in_repository(
        self, 
        repo_content: Dict[str, Any],
        search_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Discover patterns in repository content.

        Args:
            repo_content: Repository content from repomix
            search_patterns: Optional search patterns to use

        Returns:
            Dict containing pattern discovery results
        """
        start_time = time.time()

        self.logger.log_step_start(
            "pattern_discovery",
            f"Pattern discovery for {self.database_name} in {self.repo_owner}/{self.repo_name}",
            {"database_name": self.database_name, "repository": f"{self.repo_owner}/{self.repo_name}"},
        )

        try:
            # Generate default search patterns if not provided
            if not search_patterns:
                search_patterns = self._generate_search_patterns()

            # Extract files from repository content
            files = self._extract_files_from_repo_content(repo_content)
            
            # Perform pattern matching
            matched_files = await self._match_patterns_in_files(files, search_patterns)
            
            # Classify files by source type
            files_by_type = self._categorize_files_by_source_type(matched_files)
            
            # Calculate confidence distribution
            confidence_dist = self._calculate_confidence_distribution(matched_files)
            
            # Generate discovery summary
            discovery_result = {
                "database_name": self.database_name,
                "repository": f"{self.repo_owner}/{self.repo_name}",
                "tenant_id": self.tenant_id,
                "total_files": len(files),
                "matched_files": len(matched_files),
                "files": matched_files,
                "files_by_type": files_by_type,
                "search_patterns": search_patterns,
                "confidence_distribution": confidence_dist,
                "success": True,
                "duration": time.time() - start_time,
            }

            # Log discovery results
            await self._log_pattern_discovery_results(discovery_result)

            self.logger.log_step_end("pattern_discovery", discovery_result, success=True)

            return discovery_result

        except Exception as e:
            self.logger.log_error("Pattern discovery failed", e)
            raise

    def _generate_search_patterns(self) -> List[str]:
        """Generate search patterns for the database."""
        return [
            f"\\b{self.database_name}\\b",
            f"'{self.database_name}'",
            f'"{self.database_name}"',
            f"{self.database_name}\\.",
            f"database.*{self.database_name}",
            f"db.*{self.database_name}",
        ]

    def _extract_files_from_repo_content(self, repo_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract files from repository content."""
        files = []
        
        # Handle different repo content formats
        if "files" in repo_content:
            files = repo_content["files"]
        elif "content" in repo_content:
            # Parse content if it's a text format
            content = repo_content["content"]
            files = self._parse_repo_content_text(content)
        
        return files

    def _parse_repo_content_text(self, content: str) -> List[Dict[str, Any]]:
        """Parse repository content text format."""
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

    async def _match_patterns_in_files(
        self, files: List[Dict[str, Any]], search_patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Match search patterns in files."""
        matched_files = []

        for file_info in files:
            file_path = file_info.get("path", "")
            file_content = file_info.get("content", "")

            # Check for pattern matches
            matches = []
            confidence = 0.0

            for pattern in search_patterns:
                import re
                pattern_matches = re.findall(pattern, file_content, re.IGNORECASE)
                if pattern_matches:
                    matches.extend(pattern_matches)
                    confidence += 1.0 / len(search_patterns)

            if matches:
                matched_files.append({
                    "path": file_path,
                    "content": file_content,
                    "matches": matches,
                    "confidence": min(confidence, 1.0),
                    "match_count": len(matches),
                })

        return matched_files

    def _categorize_files_by_source_type(
        self, files: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize files by source type."""
        files_by_type = defaultdict(list)

        for file_info in files:
            file_path = file_info.get("path", "")
            file_content = file_info.get("content", "")

            # Classify file
            classification = self.source_classifier.classify_file(file_path, file_content)
            source_type = classification.source_type.value if classification.source_type else "unknown"
            
            files_by_type[source_type].append(file_info)

        return dict(files_by_type)

    def _calculate_confidence_distribution(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate confidence distribution for matched files."""
        distribution = {
            "high_confidence": 0,  # >= 0.8
            "medium_confidence": 0,  # 0.5 - 0.8
            "low_confidence": 0,   # < 0.5
        }

        for file_info in files:
            confidence = file_info.get("confidence", 0.0)
            
            if confidence >= 0.8:
                distribution["high_confidence"] += 1
            elif confidence >= 0.5:
                distribution["medium_confidence"] += 1
            else:
                distribution["low_confidence"] += 1

        return distribution

    async def _log_pattern_discovery_results(self, discovery_result: Dict[str, Any]):
        """Log pattern discovery results with structured visualization."""
        try:
            files_by_type = discovery_result.get("files_by_type", {})
            confidence_dist = discovery_result.get("confidence_distribution", {})

            # Log file type distribution table
            if files_by_type:
                table_data = []
                for file_type, files in files_by_type.items():
                    table_data.append({
                        "file_type": file_type.title(),
                        "count": len(files),
                        "status": "✅",
                    })

                self.logger.log_table(
                    f"Pattern Discovery Results: {self.repo_owner}/{self.repo_name}",
                    table_data
                )

            # Log confidence distribution
            if confidence_dist:
                conf_table = [
                    {"confidence_level": "High (≥80%)", "count": confidence_dist.get("high_confidence", 0)},
                    {"confidence_level": "Medium (50-80%)", "count": confidence_dist.get("medium_confidence", 0)},
                    {"confidence_level": "Low (<50%)", "count": confidence_dist.get("low_confidence", 0)},
                ]
                
                self.logger.log_table("Confidence Distribution", conf_table)

            # Log summary metrics
            total_files = discovery_result.get("total_files", 0)
            matched_files = discovery_result.get("matched_files", 0)
            match_rate = (matched_files / total_files * 100) if total_files > 0 else 0

            self.logger.log_info(
                f"Pattern Discovery Summary: {matched_files}/{total_files} files matched ({match_rate:.1f}%)"
            )

        except Exception as e:
            self.logger.log_warning(f"Failed to create visual logs for pattern discovery: {e}")


class AgenticFileProcessor:
    """
    AI-powered file processor with Manager integration.
    
    Processes files in batches using Azure OpenAI for intelligent refactoring.
    """

    def __init__(
        self,
        source_classifier: SourceTypeClassifier,
        contextual_rules_engine: Any,
        github_client: Any,
        repo_owner: str,
        repo_name: str,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Initialize the AgenticFileProcessor.

        Args:
            source_classifier: Source type classifier instance
            contextual_rules_engine: Contextual rules engine instance
            github_client: GitHub MCP client instance
            repo_owner: Repository owner name
            repo_name: Repository name
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.source_classifier = source_classifier
        self.contextual_rules_engine = contextual_rules_engine
        self.github_client = github_client
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"agentic_processor_{repo_owner}_{repo_name}"

        # Initialize Azure OpenAI client
        self.ai_client = self._initialize_ai_client()

        # Initialize logger
        config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id=self.workflow_id, config=config)

    def _initialize_ai_client(self):
        """Initialize Azure OpenAI client using Manager configuration."""
        try:
            api_key = getattr(manager_config, 'AZURE_OPENAI_API_KEY', None)
            endpoint = getattr(manager_config, 'AZURE_OPENAI_ENDPOINT', None)

            if not api_key:
                self.logger.log_warning("Azure OpenAI API key not configured")
                return None

            from openai import AsyncAzureOpenAI
            
            client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version="2024-02-15-preview"
            )
            
            return client

        except Exception as e:
            self.logger.log_error("Failed to initialize Azure OpenAI client", e)
            return None

    def _build_agent_prompt(
        self,
        batch: List[Dict[str, str]],
        rules: Dict[str, Any],
        source_type: SourceType,
    ) -> str:
        """Build a detailed prompt for the agent to process a batch of files."""
        database_name = getattr(self.contextual_rules_engine, "database_name", "unknown")

        prompt = f"""You are an expert code refactoring agent tasked with decommissioning a database named '{database_name}'.
You will be given a batch of files of type '{source_type.value}' and a set of rules to apply.
Your task is to analyze each file and apply the necessary code modifications based on the rules.

**Database Decommissioning Context:**
- Database name: {database_name}
- Target repository: {self.repo_owner}/{self.repo_name}
- File type: {source_type.value}
- Tenant: {self.tenant_id or 'default'}

**Rules:**
{json.dumps(rules, indent=2)}

**Files to Process:**
"""

        for file_info in batch:
            prompt += f"""---

**File Path:** {file_info["file_path"]}

**File Content:**
```
{file_info["file_content"]}
```
"""

        prompt += """---

Please return a JSON object with a key for each file path processed. The value for each key should be an object containing the new file content under the key 'modified_content'.

Example response format:
{
    "path/to/file1.py": {
        "modified_content": "... new content for file1 ..."
    },
    "path/to/file2.js": {
        "modified_content": "... new content for file2 ..."
    }
}

Important guidelines:
- Only modify files that actually reference the database
- Preserve code structure and functionality where possible
- Add comments explaining the changes made
- Ensure the modified code is syntactically correct
"""
        return prompt

    async def _invoke_agent_on_batch(
        self, prompt: str, batch: List[Dict[str, str]]
    ) -> List[FileProcessingResult]:
        """Invoke the Azure OpenAI agent with the prompt and process the response."""
        try:
            if not self.ai_client:
                # Fallback to no-op processing if AI client not available
                self.logger.log_warning("AI client not available, skipping agent processing")
                return [
                    FileProcessingResult(
                        file_path=f["file_path"],
                        source_type=self.source_classifier.classify_file(
                            f["file_path"], f.get("file_content", "")
                        ).source_type,
                        success=True,
                        total_changes=0,
                        rules_applied=[],
                        error_message="AI client not available",
                    )
                    for f in batch
                ]

            # Use Azure OpenAI deployment name from Manager configuration
            deployment_name = getattr(manager_config, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')

            response = await self.ai_client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant designed to output JSON for database decommissioning tasks.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent results
            )

            response_content = response.choices[0].message.content
            agent_results = json.loads(response_content)

            batch_results = []
            for file_info in batch:
                file_path = file_info["file_path"]
                original_content = file_info["file_content"]

                if (
                    file_path in agent_results
                    and "modified_content" in agent_results[file_path]
                ):
                    modified_content = agent_results[file_path]["modified_content"]
                    changes_made = 1 if modified_content != original_content else 0

                    if changes_made > 0:
                        # Update file content through contextual rules engine
                        await self.contextual_rules_engine._update_file_content(
                            self.github_client,
                            self.repo_owner,
                            self.repo_name,
                            file_path,
                            modified_content,
                        )

                    batch_results.append(
                        FileProcessingResult(
                            file_path=file_path,
                            source_type=self.source_classifier.classify_file(
                                file_path, original_content
                            ).source_type,
                            success=True,
                            total_changes=changes_made,
                            rules_applied=["ai_agent_processing"],
                        )
                    )
                else:
                    # Agent did not return modifications for this file
                    batch_results.append(
                        FileProcessingResult(
                            file_path=file_path,
                            source_type=self.source_classifier.classify_file(
                                file_path, original_content
                            ).source_type,
                            success=True,
                            total_changes=0,
                            rules_applied=[],
                        )
                    )

            return batch_results

        except Exception as e:
            self.logger.log_error(f"Error invoking AI agent or processing response: {e}")
            return [
                FileProcessingResult(
                    file_path=f["file_path"],
                    source_type=self.source_classifier.classify_file(
                        f["file_path"], f.get("file_content", "")
                    ).source_type,
                    success=False,
                    total_changes=0,
                    rules_applied=[],
                    error_message=str(e),
                )
                for f in batch
            ]

    async def process_files(
        self, files_to_process: List[Dict[str, str]], batch_size: int = 3
    ) -> List[FileProcessingResult]:
        """
        Classify, batch, and process files using an agentic workflow.

        Args:
            files_to_process: List of file dictionaries with path and content
            batch_size: Number of files to process in each batch

        Returns:
            List of FileProcessingResult objects
        """
        self.logger.log_info(
            f"Starting agentic processing for {len(files_to_process)} files with batch size {batch_size}"
        )

        # 1. Classify and group files by source type
        categorized_files = defaultdict(list)
        for file_info in files_to_process:
            file_path = file_info["file_path"]

            # Ensure content is available for classification
            if "file_content" not in file_info or file_info["file_content"] is None:
                self.logger.log_warning(f"Skipping {file_path} due to missing content")
                continue

            classification = self.source_classifier.classify_file(
                file_path, file_info["file_content"]
            )
            categorized_files[classification.source_type].append(file_info)

        all_results = []

        # 2. Process each category in batches
        for source_type, files in categorized_files.items():
            self.logger.log_info(
                f"Processing category '{source_type.value}' with {len(files)} files"
            )

            # Process files in batches
            for i in range(0, len(files), batch_size):
                batch = files[i : i + batch_size]
                self.logger.log_info(
                    f"Processing batch of {len(batch)} files for category {source_type.value}"
                )

                # Get rules for the current source_type
                applicable_rules = self.contextual_rules_engine._get_applicable_rules(
                    source_type, []
                )

                # Construct a prompt for the agent with the batch of files and rules
                prompt = self._build_agent_prompt(batch, applicable_rules, source_type)
                
                # Invoke the agent and process the results
                batch_results = await self._invoke_agent_on_batch(prompt, batch)
                all_results.extend(batch_results)

        self.logger.log_info(
            f"Agentic processing finished. Processed {len(all_results)} files"
        )
        return all_results


# Legacy compatibility functions for GraphMCP integration
async def process_discovered_files_with_rules(
    context: Any,
    discovery_result: Dict[str, Any],
    database_name: str,
    repo_owner: str,
    repo_name: str,
    contextual_rules_engine: Any,
    source_classifier: SourceTypeClassifier,
    logger: Any,
) -> Dict[str, Any]:
    """Legacy compatibility function for processing discovered files."""
    try:
        discovered_files = discovery_result.get("files", [])

        # Use AgenticFileProcessor with Manager integration
        agentic_processor = AgenticFileProcessor(
            source_classifier=source_classifier,
            contextual_rules_engine=contextual_rules_engine,
            github_client=context.clients.get("ovr_github"),
            repo_owner=repo_owner,
            repo_name=repo_name,
        )

        results = await agentic_processor.process_files(discovered_files)
        files_processed = len(results)
        files_modified = sum(1 for r in results if r.total_changes > 0)

        return {"files_processed": files_processed, "files_modified": files_modified}

    except Exception as e:
        logger.log_error("Failed to process discovered files with rules", e)
        return {"files_processed": 0, "files_modified": 0}


async def log_pattern_discovery_visual(
    workflow_id: Optional[str],
    discovery_result: Dict[str, Any],
    repo_owner: str,
    repo_name: str,
    logger: Any,
) -> None:
    """Legacy compatibility function for logging pattern discovery results."""
    processor = PatternDiscoveryProcessor("legacy_db", repo_owner, repo_name, workflow_id=workflow_id)
    await processor._log_pattern_discovery_results(discovery_result)


def categorize_files_by_source_type(
    files: List[Dict[str, Any]], source_classifier: SourceTypeClassifier
) -> Dict[SourceType, List[Dict[str, Any]]]:
    """Legacy compatibility function for categorizing files by source type."""
    processor = PatternDiscoveryProcessor("legacy_db", "owner", "repo")
    return processor._categorize_files_by_source_type(files)


def calculate_processing_metrics(results: List[FileProcessingResult]) -> Dict[str, Any]:
    """Calculate processing metrics from file processing results."""
    total_files = len(results)
    successful_files = sum(1 for r in results if r.success)
    failed_files = total_files - successful_files
    total_changes = sum(r.total_changes for r in results)

    # Group by source type
    by_source_type = defaultdict(list)
    for result in results:
        by_source_type[result.source_type].append(result)

    source_type_metrics = {}
    for source_type, type_results in by_source_type.items():
        source_type_metrics[source_type.value] = {
            "total_files": len(type_results),
            "successful_files": sum(1 for r in type_results if r.success),
            "total_changes": sum(r.total_changes for r in type_results),
        }

    return {
        "total_files": total_files,
        "successful_files": successful_files,
        "failed_files": failed_files,
        "total_changes": total_changes,
        "success_rate": (
            (successful_files / total_files * 100) if total_files > 0 else 0
        ),
        "by_source_type": source_type_metrics,
    }