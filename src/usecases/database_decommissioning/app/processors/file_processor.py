"""
File Processor for Database Decommissioning.

This module provides file processing functionality enhanced for Manager integration
while preserving GraphMCP framework compatibility.

Manager Integration:
- Manager-specific file handling patterns
- Enhanced logging and metrics
- Tenant context processing

GraphMCP Preservation:
- FileDecommissionProcessor functionality
- Processing result structures
- Error handling patterns
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.utils.source_type_classifier import SourceType, SourceTypeClassifier
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..models import FileProcessingResult
from ..utils import create_logger_for_workflow


class FileProcessor:
    """
    File processor with Manager integration.
    
    Processes files for database decommissioning with enhanced Manager features.
    """

    def __init__(
        self,
        database_name: str,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Initialize file processor.

        Args:
            database_name: Name of database being decommissioned
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"file_processor_{int(time.time())}"

        # Initialize components
        self.source_classifier = SourceTypeClassifier()
        
        # Initialize logger
        self.logger = create_logger_for_workflow(
            self.workflow_id, self.database_name, self.tenant_id
        )

    async def process_files(
        self,
        source_dir: str,
        database_name: str,
        output_dir: Optional[str] = None,
        ticket_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process files in source directory for database decommissioning.

        Args:
            source_dir: Source directory containing files to process
            database_name: Name of database being decommissioned
            output_dir: Optional output directory for processed files
            ticket_id: Optional ticket identifier for tracking

        Returns:
            Dict containing processing results
        """
        start_time = time.time()

        self.logger.log_step_start(
            "file_processing",
            f"Processing files in {source_dir} for database {database_name}",
            {
                "source_dir": source_dir,
                "database_name": database_name,
                "output_dir": output_dir,
                "ticket_id": ticket_id,
                "tenant_id": self.tenant_id,
            },
        )

        try:
            # Validate source directory
            source_path = Path(source_dir)
            if not source_path.exists():
                raise FileNotFoundError(f"Source directory not found: {source_dir}")

            # Set up output directory
            if not output_dir:
                output_dir = f"{source_dir}_decommissioned"
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Discover files to process
            files_to_process = self._discover_files(source_path)
            
            # Process files with database decommissioning logic
            processing_results = await self._process_file_batch(
                files_to_process, source_path, output_path, database_name
            )

            # Calculate processing metrics
            metrics = self._calculate_processing_metrics(processing_results)

            # Generate strategies applied summary
            strategies_applied = self._extract_strategies_applied(processing_results)

            result = {
                "database_name": database_name,
                "source_directory": source_dir,
                "output_directory": output_dir,
                "processed_files": [r.file_path for r in processing_results],
                "strategies_applied": strategies_applied,
                "processing_results": processing_results,
                "metrics": metrics,
                "ticket_id": ticket_id,
                "tenant_id": self.tenant_id,
                "success": True,
                "duration": time.time() - start_time,
            }

            # Log processing summary
            self._log_processing_summary(result)

            self.logger.log_step_end("file_processing", result, success=True)

            return result

        except Exception as e:
            self.logger.log_error("File processing failed", e)
            raise

    def _discover_files(self, source_path: Path) -> List[Path]:
        """Discover files to process in source directory."""
        files_to_process = []

        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                # Skip binary files and common exclusions
                if self._should_process_file(file_path):
                    files_to_process.append(file_path)

        self.logger.log_info(f"Discovered {len(files_to_process)} files to process")
        return files_to_process

    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        # Skip binary files
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.zip', '.tar', '.gz',
        }
        
        if file_path.suffix.lower() in binary_extensions:
            return False

        # Skip hidden files and directories
        if any(part.startswith('.') for part in file_path.parts):
            return False

        # Skip common build and dependency directories
        skip_dirs = {'node_modules', '__pycache__', '.git', 'target', 'build', 'dist'}
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            return False

        return True

    async def _process_file_batch(
        self,
        files: List[Path],
        source_path: Path,
        output_path: Path,
        database_name: str,
    ) -> List[FileProcessingResult]:
        """Process a batch of files."""
        processing_results = []

        for file_path in files:
            try:
                result = await self._process_single_file(
                    file_path, source_path, output_path, database_name
                )
                processing_results.append(result)
            except Exception as e:
                self.logger.log_error(f"Failed to process file {file_path}", e)
                processing_results.append(
                    FileProcessingResult(
                        file_path=str(file_path.relative_to(source_path)),
                        source_type=SourceType.DOCUMENTATION,  # Default fallback
                        success=False,
                        total_changes=0,
                        error_message=str(e),
                    )
                )

        return processing_results

    async def _process_single_file(
        self,
        file_path: Path,
        source_path: Path,
        output_path: Path,
        database_name: str,
    ) -> FileProcessingResult:
        """Process a single file."""
        try:
            # Read file content
            file_content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Classify file type
            relative_path = file_path.relative_to(source_path)
            classification = self.source_classifier.classify_file(str(relative_path), file_content)
            
            # Determine processing strategy
            strategy = self._determine_processing_strategy(classification.source_type, file_content, database_name)
            
            # Apply processing strategy
            modified_content, changes_made = await self._apply_processing_strategy(
                strategy, file_content, database_name, str(relative_path)
            )

            # Write processed file to output directory
            output_file_path = output_path / relative_path
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(modified_content, encoding='utf-8')

            return FileProcessingResult(
                file_path=str(relative_path),
                source_type=classification.source_type,
                success=True,
                total_changes=changes_made,
                rules_applied=[strategy],
            )

        except Exception as e:
            return FileProcessingResult(
                file_path=str(file_path.relative_to(source_path)),
                source_type=SourceType.DOCUMENTATION,
                success=False,
                total_changes=0,
                error_message=str(e),
            )

    def _determine_processing_strategy(
        self, source_type: SourceType, file_content: str, database_name: str
    ) -> str:
        """Determine processing strategy based on file type and content."""
        # Check if file contains database references
        import re
        
        db_patterns = [
            f"\\b{database_name}\\b",
            f"'{database_name}'",
            f'"{database_name}"',
            f"{database_name}\\.",
        ]
        
        has_db_reference = any(
            re.search(pattern, file_content, re.IGNORECASE) for pattern in db_patterns
        )

        if not has_db_reference:
            return "no_change"

        # Determine strategy based on source type
        if source_type == SourceType.INFRASTRUCTURE:
            return "infrastructure"
        elif source_type == SourceType.CONFIGURATION:
            return "configuration"
        elif source_type == SourceType.CODE:
            return "code"
        else:
            return "documentation"

    async def _apply_processing_strategy(
        self, strategy: str, content: str, database_name: str, file_path: str
    ) -> tuple[str, int]:
        """Apply processing strategy to file content."""
        if strategy == "no_change":
            return content, 0

        import re
        modified_content = content
        changes_made = 0

        # Apply database reference processing based on strategy
        if strategy == "infrastructure":
            # Infrastructure files: Comment out or remove database references
            modified_content, changes_made = self._process_infrastructure_file(
                content, database_name
            )
        elif strategy == "configuration":
            # Configuration files: Update or remove database configuration
            modified_content, changes_made = self._process_configuration_file(
                content, database_name
            )
        elif strategy == "code":
            # Code files: Add deprecation warnings and comments
            modified_content, changes_made = self._process_code_file(
                content, database_name, file_path
            )
        elif strategy == "documentation":
            # Documentation files: Add deprecation notices
            modified_content, changes_made = self._process_documentation_file(
                content, database_name
            )

        return modified_content, changes_made

    def _process_infrastructure_file(self, content: str, database_name: str) -> tuple[str, int]:
        """Process infrastructure files (Terraform, Docker, etc.)."""
        import re
        
        # Comment out lines that reference the database
        lines = content.split('\n')
        modified_lines = []
        changes_made = 0

        for line in lines:
            if re.search(f"\\b{database_name}\\b", line, re.IGNORECASE):
                if not line.strip().startswith('#'):
                    modified_lines.append(f"# DECOMMISSIONED: {line}")
                    changes_made += 1
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

        return '\n'.join(modified_lines), changes_made

    def _process_configuration_file(self, content: str, database_name: str) -> tuple[str, int]:
        """Process configuration files (JSON, YAML, etc.)."""
        import re
        
        # Add deprecation comments and mark for removal
        lines = content.split('\n')
        modified_lines = []
        changes_made = 0

        for line in lines:
            if re.search(f"\\b{database_name}\\b", line, re.IGNORECASE):
                # Add deprecation comment before the line
                if line.strip() and not any(modified_lines[-1:]) or not modified_lines[-1].strip().startswith('#'):
                    modified_lines.append(f"# DEPRECATED: Database {database_name} has been decommissioned")
                modified_lines.append(line)
                changes_made += 1
            else:
                modified_lines.append(line)

        return '\n'.join(modified_lines), changes_made

    def _process_code_file(self, content: str, database_name: str, file_path: str) -> tuple[str, int]:
        """Process code files (Python, JavaScript, etc.)."""
        import re
        
        # Add deprecation warnings and comments
        lines = content.split('\n')
        modified_lines = []
        changes_made = 0
        added_import = False

        for i, line in enumerate(lines):
            if re.search(f"\\b{database_name}\\b", line, re.IGNORECASE):
                # Add deprecation warning before first database reference
                if not added_import and file_path.endswith('.py'):
                    modified_lines.append("import warnings")
                    modified_lines.append("")
                    added_import = True
                
                # Add warning comment
                indent = len(line) - len(line.lstrip())
                comment_prefix = "#" if file_path.endswith('.py') else "//"
                modified_lines.append(f"{' ' * indent}{comment_prefix} WARNING: Database {database_name} has been decommissioned")
                
                if file_path.endswith('.py'):
                    modified_lines.append(f"{' ' * indent}warnings.warn('Database {database_name} has been decommissioned', DeprecationWarning)")
                
                modified_lines.append(line)
                changes_made += 1
            else:
                modified_lines.append(line)

        return '\n'.join(modified_lines), changes_made

    def _process_documentation_file(self, content: str, database_name: str) -> tuple[str, int]:
        """Process documentation files (Markdown, text, etc.)."""
        import re
        
        # Add deprecation notice at the top of the document
        if re.search(f"\\b{database_name}\\b", content, re.IGNORECASE):
            deprecation_notice = f"""
> **⚠️ DEPRECATION NOTICE**  
> The {database_name} database has been decommissioned and is no longer available.  
> This documentation is kept for historical reference only.

"""
            return deprecation_notice + content, 1
        
        return content, 0

    def _calculate_processing_metrics(self, results: List[FileProcessingResult]) -> Dict[str, Any]:
        """Calculate processing metrics."""
        total_files = len(results)
        successful_files = sum(1 for r in results if r.success)
        failed_files = total_files - successful_files
        total_changes = sum(r.total_changes for r in results)

        # Group by strategy (extracted from rules_applied)
        by_strategy = {}
        for result in results:
            strategies = result.rules_applied or ["no_strategy"]
            for strategy in strategies:
                if strategy not in by_strategy:
                    by_strategy[strategy] = {"count": 0, "changes": 0}
                by_strategy[strategy]["count"] += 1
                by_strategy[strategy]["changes"] += result.total_changes

        return {
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "total_changes": total_changes,
            "success_rate": (successful_files / total_files * 100) if total_files > 0 else 0,
            "by_strategy": by_strategy,
        }

    def _extract_strategies_applied(self, results: List[FileProcessingResult]) -> Dict[str, str]:
        """Extract strategies applied to each file."""
        strategies = {}
        for result in results:
            if result.rules_applied:
                strategies[result.file_path] = result.rules_applied[0]
            else:
                strategies[result.file_path] = "no_change"
        return strategies

    def _log_processing_summary(self, result: Dict[str, Any]):
        """Log processing summary with structured data."""
        metrics = result.get("metrics", {})
        
        # Log metrics table
        metrics_table = [
            {"metric": "Total Files", "value": str(metrics.get("total_files", 0))},
            {"metric": "Successful", "value": str(metrics.get("successful_files", 0))},
            {"metric": "Failed", "value": str(metrics.get("failed_files", 0))},
            {"metric": "Total Changes", "value": str(metrics.get("total_changes", 0))},
            {"metric": "Success Rate", "value": f"{metrics.get('success_rate', 0):.1f}%"},
        ]
        
        self.logger.log_table("File Processing Metrics", metrics_table)

        # Log strategy summary
        by_strategy = metrics.get("by_strategy", {})
        if by_strategy:
            strategy_table = [
                {
                    "strategy": strategy.title(),
                    "files": str(data["count"]),
                    "changes": str(data["changes"]),
                }
                for strategy, data in by_strategy.items()
            ]
            
            self.logger.log_table("Processing Strategy Summary", strategy_table)


# Legacy compatibility class for GraphMCP integration
class FileDecommissionProcessor:
    """Legacy compatibility class for GraphMCP integration."""
    
    def __init__(self):
        """Initialize legacy file processor."""
        self.processor = None
    
    async def process_files(
        self, source_dir: str, database_name: str, output_dir: str
    ) -> bool:
        """Legacy compatibility method."""
        try:
            self.processor = FileProcessor(database_name)
            result = await self.processor.process_files(source_dir, database_name, output_dir)
            return result.get("success", False)
        except Exception:
            return False