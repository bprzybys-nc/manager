"""
WorkflowState for DB Runbook Finder workflow.

This module defines the state management for the DB Runbook Finder workflow,
tracking all data and status throughout the workflow execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class WorkflowState:
    """State management for DB Runbook Finder workflow.
    
    This dataclass manages all workflow state including input parameters,
    intermediate results, and final outcomes.
    
    Attributes:
        jira_key: Jira ticket identifier (e.g., "AGENT-6")
        incident_data: Structured data from Jira ticket
        runbooks: List of runbook objects from vector search
        status: Current workflow status
        error_message: Error details if workflow fails
        created_at: Timestamp when workflow started
        updated_at: Timestamp of last state update
        performance_metrics: Timing and performance data
    """
    
    jira_key: str
    incident_data: Dict[str, Any] = field(default_factory=dict)
    runbooks: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING"
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize state after creation."""
        if not self.jira_key:
            raise ValueError("jira_key is required")
        
        # Ensure all required fields are properly initialized
        if self.incident_data is None:
            self.incident_data = {}
        if self.runbooks is None:
            self.runbooks = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

    def update_status(self, new_status: str, error_message: Optional[str] = None):
        """Update workflow status with timestamp.
        
        Args:
            new_status: New status value
            error_message: Optional error message for error states
        """
        self.status = new_status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def add_performance_metric(self, operation: str, duration_seconds: float):
        """Add performance timing data.
        
        Args:
            operation: Name of the operation (e.g., "jira_fetch", "vector_search")
            duration_seconds: Time taken for the operation
        """
        self.performance_metrics[operation] = duration_seconds

    def get_client_name(self) -> str:
        """Extract client name from incident data.
        
        Returns:
            Client name or "Unknown" if not found
        """
        return self.incident_data.get("client", "Unknown")

    def get_incident_summary(self) -> str:
        """Get formatted incident summary.
        
        Returns:
            Incident summary or "No summary available"
        """
        return self.incident_data.get("summary", "No summary available")

    def get_search_query(self) -> str:
        """Construct search query from incident data.
        
        Returns:
            Combined summary and description for search
        """
        summary = self.incident_data.get("summary", "")
        description = self.incident_data.get("description", "")
        return f"{summary} {description}".strip()

    def has_runbooks(self) -> bool:
        """Check if any runbooks were found.
        
        Returns:
            True if runbooks are available, False otherwise
        """
        return bool(self.runbooks and len(self.runbooks) > 0)

    def get_total_duration(self) -> float:
        """Calculate total workflow duration.
        
        Returns:
            Total duration in seconds
        """
        return sum(self.performance_metrics.values())

    def is_error_state(self) -> bool:
        """Check if workflow is in error state.
        
        Returns:
            True if status indicates error, False otherwise
        """
        return self.status in ["ERROR", "FAILED"]

    def is_completed(self) -> bool:
        """Check if workflow has completed (success or gap).
        
        Returns:
            True if workflow completed, False if still running or error
        """
        return self.status in ["SUCCESS", "GAP_DETECTED"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization.
        
        Returns:
            Dictionary representation of the state
        """
        return {
            "jira_key": self.jira_key,
            "incident_data": self.incident_data,
            "runbooks": self.runbooks,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "performance_metrics": self.performance_metrics
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Create WorkflowState from dictionary.
        
        Args:
            data: Dictionary containing state data
            
        Returns:
            WorkflowState instance
        """
        # Handle datetime fields
        created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        
        return cls(
            jira_key=data["jira_key"],
            incident_data=data.get("incident_data", {}),
            runbooks=data.get("runbooks", []),
            status=data.get("status", "PENDING"),
            error_message=data.get("error_message"),
            created_at=created_at,
            updated_at=updated_at,
            performance_metrics=data.get("performance_metrics", {})
        )

    def __str__(self) -> str:
        """String representation of the workflow state."""
        return f"WorkflowState(jira_key={self.jira_key}, status={self.status}, runbooks={len(self.runbooks)})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"WorkflowState(jira_key='{self.jira_key}', status='{self.status}', "
                f"runbooks_count={len(self.runbooks)}, client='{self.get_client_name()}')")