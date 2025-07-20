"""
Database Decommissioning Workflow Data Models.

This module contains data models for the database decommissioning workflow,
enhanced for Manager integration while preserving GraphMCP framework compatibility.

Following Manager patterns:
- Pydantic BaseModel for FastAPI integration
- Manager-specific fields (tenant_id, user_id, etc.)
- Proper validation and serialization
- FastAPI response models

Preserving GraphMCP patterns:
- Dataclass compatibility for workflow context
- Timestamp tracking
- Pickle-safe for state management
- Utility methods for state management
"""

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

# Import from GraphMCP framework for compatibility
try:
    from src.frameworks.graphmcp.utils.source_type_classifier import SourceType
except ImportError:
    # Fallback if GraphMCP not available
    class SourceType(Enum):
        INFRASTRUCTURE = "infrastructure"
        CONFIGURATION = "configuration"
        CODE = "code"
        DOCUMENTATION = "documentation"


class ValidationResult(Enum):
    """Enumeration of validation results."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class FileProcessingResult:
    """
    Result from processing a file during decommissioning.

    Compatibility class for AgenticFileProcessor with enhanced tracking.
    Maintains dataclass structure for GraphMCP compatibility.
    """
    file_path: str
    source_type: SourceType
    success: bool
    total_changes: int
    rules_applied: Optional[List[str]] = None
    error_message: Optional[str] = None
    timestamp: Optional[float] = None
    processing_duration_ms: Optional[int] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.rules_applied is None:
            self.rules_applied = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileProcessingResult':
        """Create instance from dictionary."""
        # Handle enum conversion
        if isinstance(data.get('source_type'), str):
            data['source_type'] = SourceType(data['source_type'])
        return cls(**data)


# FastAPI-compatible models for Manager API integration
class FileProcessingResultResponse(BaseModel):
    """FastAPI response model for file processing results."""
    file_path: str
    source_type: str
    success: bool
    total_changes: int
    rules_applied: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: Optional[float] = None
    processing_duration_ms: Optional[int] = None

    @classmethod
    def from_dataclass(cls, result: FileProcessingResult) -> 'FileProcessingResultResponse':
        """Convert from dataclass to Pydantic model."""
        return cls(
            file_path=result.file_path,
            source_type=result.source_type.value if result.source_type else "unknown",
            success=result.success,
            total_changes=result.total_changes,
            rules_applied=result.rules_applied or [],
            error_message=result.error_message,
            timestamp=result.timestamp,
            processing_duration_ms=result.processing_duration_ms,
        )


@dataclass
class WorkflowConfig:
    """
    Configuration for database decommissioning workflow.

    Enhanced for Manager integration with tenant and user context.
    """
    database_name: str
    repo_owner: str
    repo_name: str
    # Manager-specific fields
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    # Workflow configuration
    max_parallel_steps: int = 4
    default_timeout: int = 120
    log_file: str = "dbworkflow.log"
    enable_console_logging: bool = True
    enable_json_logging: bool = True
    enable_slack_notifications: bool = True
    dry_run: bool = False
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowConfig':
        """Create instance from dictionary."""
        return cls(**data)


class WorkflowConfigRequest(BaseModel):
    """FastAPI request model for workflow configuration."""
    database_name: str = Field(..., description="Name of the database to decommission")
    repo_owner: str = Field(..., description="Repository owner")
    repo_name: str = Field(..., description="Repository name")
    max_parallel_steps: int = Field(default=4, ge=1, le=10, description="Maximum parallel steps")
    default_timeout: int = Field(default=120, ge=30, le=600, description="Default timeout in seconds")
    enable_slack_notifications: bool = Field(default=True, description="Enable Slack notifications")
    dry_run: bool = Field(default=False, description="Run in dry-run mode")

    def to_dataclass(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None) -> WorkflowConfig:
        """Convert to dataclass for workflow processing."""
        return WorkflowConfig(
            database_name=self.database_name,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            tenant_id=tenant_id,
            user_id=user_id,
            max_parallel_steps=self.max_parallel_steps,
            default_timeout=self.default_timeout,
            enable_slack_notifications=self.enable_slack_notifications,
            dry_run=self.dry_run,
        )


class WorkflowConfigResponse(BaseModel):
    """FastAPI response model for workflow configuration."""
    database_name: str
    repo_owner: str
    repo_name: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    max_parallel_steps: int
    default_timeout: int
    enable_slack_notifications: bool
    dry_run: bool
    timestamp: Optional[float] = None

    @classmethod
    def from_dataclass(cls, config: WorkflowConfig) -> 'WorkflowConfigResponse':
        """Convert from dataclass to Pydantic model."""
        return cls(
            database_name=config.database_name,
            repo_owner=config.repo_owner,
            repo_name=config.repo_name,
            tenant_id=config.tenant_id,
            user_id=config.user_id,
            max_parallel_steps=config.max_parallel_steps,
            default_timeout=config.default_timeout,
            enable_slack_notifications=config.enable_slack_notifications,
            dry_run=config.dry_run,
            timestamp=config.timestamp,
        )


@dataclass
class QualityAssuranceResult:
    """
    Result from quality assurance checks.

    Comprehensive QA result with detailed metrics and Manager integration.
    """
    database_reference_check: ValidationResult
    rule_compliance_check: ValidationResult
    service_integrity_check: ValidationResult
    overall_status: ValidationResult
    details: Dict[str, Any]
    recommendations: List[str]
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.recommendations is None:
            self.recommendations = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "database_reference_check": self.database_reference_check.value,
            "rule_compliance_check": self.rule_compliance_check.value,
            "service_integrity_check": self.service_integrity_check.value,
            "overall_status": self.overall_status.value,
            "details": self.details,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityAssuranceResult':
        """Create instance from dictionary."""
        # Handle enum conversion
        data['database_reference_check'] = ValidationResult(data['database_reference_check'])
        data['rule_compliance_check'] = ValidationResult(data['rule_compliance_check'])
        data['service_integrity_check'] = ValidationResult(data['service_integrity_check'])
        data['overall_status'] = ValidationResult(data['overall_status'])
        return cls(**data)


class QualityAssuranceResponse(BaseModel):
    """FastAPI response model for quality assurance results."""
    database_reference_check: str
    rule_compliance_check: str
    service_integrity_check: str
    overall_status: str
    details: Dict[str, Any]
    recommendations: List[str]
    timestamp: Optional[float] = None

    @classmethod
    def from_dataclass(cls, qa_result: QualityAssuranceResult) -> 'QualityAssuranceResponse':
        """Convert from dataclass to Pydantic model."""
        return cls(
            database_reference_check=qa_result.database_reference_check.value,
            rule_compliance_check=qa_result.rule_compliance_check.value,
            service_integrity_check=qa_result.service_integrity_check.value,
            overall_status=qa_result.overall_status.value,
            details=qa_result.details,
            recommendations=qa_result.recommendations,
            timestamp=qa_result.timestamp,
        )


@dataclass
class WorkflowStepResult:
    """
    Result from a single workflow step execution.

    Standardized step result with metrics and context for Manager integration.
    """
    step_name: str
    step_id: str
    success: bool
    duration_seconds: float
    result_data: Dict[str, Any]
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.warnings is None:
            self.warnings = []
        if self.metrics is None:
            self.metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStepResult':
        """Create instance from dictionary."""
        return cls(**data)


class WorkflowStepResponse(BaseModel):
    """FastAPI response model for workflow step results."""
    step_name: str
    step_id: str
    success: bool
    duration_seconds: float
    result_data: Dict[str, Any]
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None

    @classmethod
    def from_dataclass(cls, step_result: WorkflowStepResult) -> 'WorkflowStepResponse':
        """Convert from dataclass to Pydantic model."""
        return cls(
            step_name=step_result.step_name,
            step_id=step_result.step_id,
            success=step_result.success,
            duration_seconds=step_result.duration_seconds,
            result_data=step_result.result_data,
            error_message=step_result.error_message,
            warnings=step_result.warnings or [],
            metrics=step_result.metrics or {},
            timestamp=step_result.timestamp,
        )


@dataclass
class DecommissioningSummary:
    """
    Summary of the entire decommissioning workflow.

    Comprehensive workflow summary with all key metrics and Manager integration.
    """
    workflow_id: str
    database_name: str
    total_files_processed: int
    successful_files: int
    failed_files: int
    total_changes: int
    rules_applied: List[str]
    execution_time_seconds: float
    quality_assurance: Optional[QualityAssuranceResult] = None
    github_pr_url: Optional[str] = None
    # Manager-specific fields
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = time.time()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files_processed == 0:
            return 0.0
        return (self.successful_files / self.total_files_processed) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "database_name": self.database_name,
            "total_files_processed": self.total_files_processed,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "total_changes": self.total_changes,
            "rules_applied": self.rules_applied,
            "execution_time_seconds": self.execution_time_seconds,
            "quality_assurance": (
                self.quality_assurance.to_dict() if self.quality_assurance else None
            ),
            "github_pr_url": self.github_pr_url,
            "success_rate": self.success_rate,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecommissioningSummary':
        """Create instance from dictionary."""
        # Handle nested QA result
        if data.get('quality_assurance'):
            data['quality_assurance'] = QualityAssuranceResult.from_dict(data['quality_assurance'])
        return cls(**data)


class DecommissioningSummaryResponse(BaseModel):
    """FastAPI response model for decommissioning summary."""
    workflow_id: str
    database_name: str
    total_files_processed: int
    successful_files: int
    failed_files: int
    total_changes: int
    rules_applied: List[str]
    execution_time_seconds: float
    success_rate: float
    quality_assurance: Optional[QualityAssuranceResponse] = None
    github_pr_url: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: Optional[float] = None

    @classmethod
    def from_dataclass(cls, summary: DecommissioningSummary) -> 'DecommissioningSummaryResponse':
        """Convert from dataclass to Pydantic model."""
        return cls(
            workflow_id=summary.workflow_id,
            database_name=summary.database_name,
            total_files_processed=summary.total_files_processed,
            successful_files=summary.successful_files,
            failed_files=summary.failed_files,
            total_changes=summary.total_changes,
            rules_applied=summary.rules_applied,
            execution_time_seconds=summary.execution_time_seconds,
            success_rate=summary.success_rate,
            quality_assurance=(
                QualityAssuranceResponse.from_dataclass(summary.quality_assurance) 
                if summary.quality_assurance else None
            ),
            github_pr_url=summary.github_pr_url,
            tenant_id=summary.tenant_id,
            user_id=summary.user_id,
            timestamp=summary.timestamp,
        )


# Manager API status and health models
class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatusResponse(BaseModel):
    """FastAPI response model for workflow status."""
    workflow_id: str
    status: str  # "running", "completed", "failed", "cancelled"
    database_name: Optional[str] = None
    tenant_id: Optional[str] = None
    repository: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    summary: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None  # Can contain current_step, total_steps, completion_percentage


class HealthCheckResponse(BaseModel):
    """FastAPI response model for health checks."""
    status: str = "healthy"
    timestamp: float = Field(default_factory=time.time)
    service: str = "database_decommissioning"
    version: str = "1.0.0"
    checks: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowListResponse(BaseModel):
    """FastAPI response model for workflow list."""
    workflows: List[Dict[str, Any]]
    total_count: int
    offset: int = 0
    limit: int = 50


class WorkflowExecutionRequest(BaseModel):
    """FastAPI request model for workflow execution."""
    database_name: str = Field(..., description="Name of database to decommission")
    repo_owner: str = Field(..., description="Repository owner/organization")
    repo_name: str = Field(..., description="Repository name")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenancy")
    user_id: Optional[str] = Field(None, description="User identifier")
    dry_run: bool = Field(False, description="Whether to perform a dry run without making changes")
    slack_channel: Optional[str] = Field(None, description="Slack channel for notifications")
    mcp_config_path: Optional[str] = Field(None, description="Path to MCP configuration file")
    # Workflow configuration
    max_parallel_steps: int = Field(4, description="Maximum parallel steps in workflow")
    default_timeout: int = Field(300, description="Default timeout for steps in seconds")
    stop_on_error: bool = Field(False, description="Whether to stop workflow on first error")


# Workflow execution result models
@dataclass
class WorkflowExecutionResult:
    """
    Result from executing a database decommissioning workflow.
    
    Enhanced with Manager integration while preserving GraphMCP compatibility.
    """
    workflow_id: str
    database_name: str
    success: bool
    duration: float
    step_results: Dict[str, Any]
    
    # Manager-specific fields
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # GraphMCP compatibility fields
    config: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowExecutionResult':
        """Create instance from dictionary."""
        return cls(**data)


class WorkflowExecutionResultResponse(BaseModel):
    """FastAPI response model for workflow execution results."""
    workflow_id: str
    database_name: str
    success: bool
    duration: float
    step_results: Dict[str, Any]
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None


# Error response models
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)