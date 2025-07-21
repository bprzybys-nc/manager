"""
Protocol interface definitions for the RunbookRepositoryMCP Server.

This module defines the four strategy interfaces using Python's typing.Protocol
for structural subtyping, enabling duck-typing compatibility without explicit
inheritance requirements.
"""

from typing import Protocol, List, Dict, Any, Optional
import abc


class RunbookDiscoveryStrategy(Protocol):
    """Protocol for runbook discovery operations."""
    
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        """
        Discover runbooks in specified spaces.
        
        Args:
            spaces: List of space keys to search within
            
        Returns:
            List of runbook metadata dictionaries
        """
        ...
    
    async def get_runbook_content(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific runbook content.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            Runbook content dictionary or None if not found
        """
        ...
    
    async def validate_runbook_content(self, page: Dict[str, Any]) -> bool:
        """
        Validate runbook content structure.
        
        Args:
            page: Page content to validate
            
        Returns:
            True if content is valid runbook format
        """
        ...
    
    async def extract_runbook_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from runbook page.
        
        Args:
            page: Page content to extract metadata from
            
        Returns:
            Metadata dictionary with title, tags, space, etc.
        """
        ...
    
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search runbooks by text query.
        
        Args:
            query: Search query string
            spaces: Optional list of spaces to limit search
            limit: Maximum number of results
            
        Returns:
            List of matching runbook dictionaries
        """
        ...


class VectorStorageStrategy(Protocol):
    """Protocol for vector storage and semantic search operations."""
    
    async def store_runbook_embedding(self, runbook_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Store runbook with vector embedding.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Text content to embed
            metadata: Associated metadata
            
        Returns:
            True if storage successful
        """
        ...
    
    async def search_similar_runbooks(self, query: str, limit: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Semantic search for similar runbooks.
        
        Args:
            query: Search query for similarity matching
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of similar runbooks with similarity scores
        """
        ...
    
    async def update_runbook_embedding(self, runbook_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Update existing runbook embedding.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Updated text content
            metadata: Updated metadata
            
        Returns:
            True if update successful
        """
        ...
    
    async def delete_runbook_embedding(self, runbook_id: str) -> bool:
        """
        Delete runbook from vector store.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            True if deletion successful
        """
        ...
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get vector store collection statistics.
        
        Returns:
            Statistics dictionary with counts, dimensions, etc.
        """
        ...
    
    async def list_stored_runbooks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all stored runbooks with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of stored runbook metadata
        """
        ...


class DataPersistenceStrategy(Protocol):
    """Protocol for data persistence and incident management operations."""
    
    async def save_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """
        Track runbook usage for effectiveness metrics.
        
        Args:
            runbook_id: Unique identifier for the runbook
            usage_context: Context including incident_id, user, timestamp, outcome
            
        Returns:
            Usage record ID
        """
        ...
    
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """
        Retrieve usage and effectiveness metrics.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            Metrics dictionary with usage count, success rate, etc.
        """
        ...
    
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Create incident ticket linked to runbook usage.
        
        Args:
            runbook_id: Runbook being used for incident
            context: Incident details, priority, description, etc.
            
        Returns:
            Created ticket ID
        """
        ...
    
    async def update_ticket_status(self, ticket_id: str, status: str, comment: Optional[str] = None) -> bool:
        """
        Update incident ticket with runbook execution results.
        
        Args:
            ticket_id: Ticket to update
            status: New status (open, in_progress, resolved, closed)
            comment: Optional comment with rich text formatting
            
        Returns:
            True if update successful
        """
        ...
    
    async def get_incident_history(self, incident_id: str) -> Dict[str, Any]:
        """
        Get complete incident history including runbook usage.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            History dictionary with timeline, runbooks used, outcomes
        """
        ...
    
    async def track_runbook_effectiveness(self, runbook_id: str, incident_id: str, success: bool, 
                                        resolution_time: float, notes: Optional[str] = None) -> bool:
        """
        Track runbook effectiveness for continuous improvement.
        
        Args:
            runbook_id: Runbook used
            incident_id: Associated incident
            success: Whether runbook resolved the issue
            resolution_time: Time to resolution in minutes
            notes: Optional effectiveness notes
            
        Returns:
            True if tracking successful
        """
        ...


class NotificationStrategy(Protocol):
    """Protocol for notification and communication operations."""
    
    async def send_runbook_notification(self, channel: str, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Send runbook discovery notification.
        
        Args:
            channel: Communication channel (Slack channel, email group, etc.)
            runbook_id: Runbook that was found
            context: Context including incident details, search query, etc.
            
        Returns:
            Notification/thread ID
        """
        ...
    
    async def create_approval_thread(self, channel: str, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Create interactive approval thread for runbook execution.
        
        Args:
            channel: Communication channel
            runbook_id: Runbook requiring approval
            context: Execution context and details
            
        Returns:
            Thread ID for tracking responses
        """
        ...
    
    async def update_thread_status(self, thread_id: str, status: str, results: Dict[str, Any]) -> bool:
        """
        Update thread with execution status and results.
        
        Args:
            thread_id: Thread to update
            status: Current status (pending, approved, rejected, executing, completed)
            results: Execution results or progress updates
            
        Returns:
            True if update successful
        """
        ...
    
    async def send_completion_summary(self, channel: str, summary: Dict[str, Any]) -> str:
        """
        Send workflow completion summary.
        
        Args:
            channel: Communication channel
            summary: Complete workflow results including metrics, outcomes
            
        Returns:
            Message ID
        """
        ...
    
    async def send_escalation_alert(self, channel: str, incident_id: str, escalation_context: Dict[str, Any]) -> str:
        """
        Send escalation alert when runbook execution fails or requires human intervention.
        
        Args:
            channel: Communication channel for escalation
            incident_id: Associated incident
            escalation_context: Details requiring escalation
            
        Returns:
            Alert message ID
        """
        ...
    
    async def create_thread(self, channel: str, message: str, formatting: Optional[Any] = None) -> str:
        """
        Create new communication thread.
        
        Args:
            channel: Communication channel
            message: Initial message content
            formatting: Optional formatting (bold, italic, code, etc.)
            
        Returns:
            Thread ID
        """
        ...
    
    async def send_message(self, thread_id: str, message: str, formatting: Optional[Any] = None) -> str:
        """
        Send message to existing thread.
        
        Args:
            thread_id: Existing thread
            message: Message content
            formatting: Optional formatting
            
        Returns:
            Message ID
        """
        ...