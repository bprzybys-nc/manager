"""
Abstract Base Class interface definitions for the RunbookRepositoryMCP Server.

This module defines the four strategy interfaces using Python's ABC (Abstract Base Classes)
following 2025 best practices for formal interface validation and inheritance-based contracts.
All strategy implementations must inherit from these classes.
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


# Abstract Base Classes with formal interface validation
# Following Python 2025 ABC best practices: formal interfaces with validation and error handling

class AbstractDiscoveryStrategy(ABC):
    """
    Abstract base class implementing RunbookDiscoveryStrategy protocol.
    
    Provides concrete method signatures that help detect interface drift
    and ensure all implementations maintain consistent contracts.
    """
    
    @abstractmethod
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        """Discover runbooks in specified spaces."""
        pass
    
    @abstractmethod
    async def get_runbook_content(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific runbook content."""
        pass
    
    @abstractmethod
    async def validate_runbook_content(self, page: Dict[str, Any]) -> bool:
        """Validate runbook content structure."""
        pass
    
    @abstractmethod
    async def extract_runbook_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from runbook page."""
        pass
    
    @abstractmethod
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search runbooks by text query."""
        pass
    
    async def health_check(self) -> bool:
        """
        Default health check implementation with validation.
        
        Returns:
            True if strategy is healthy and operational
            
        Note:
            Concrete implementations should override this method to provide
            actual health validation specific to their service integrations.
        """
        # Default implementation always returns True for mock/test scenarios
        # Production implementations should override with actual health checks
        return True
    
    def __init_subclass__(cls, **kwargs):
        """
        Validate subclass implementation completeness (Python 2025 best practice).
        
        This method is called when a class inherits from this ABC and helps
        ensure proper interface implementation at class definition time.
        """
        super().__init_subclass__(**kwargs)
        
        # Check if there are any abstract methods left unimplemented
        # Use the built-in __abstractmethods__ attribute for safe checking
        if hasattr(cls, '__abstractmethods__') and cls.__abstractmethods__:
            # This will be caught at instantiation time, but we can log it early
            import logging
            logger = logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
            logger.debug(f"Abstract methods pending implementation: {cls.__abstractmethods__}")
    
    @classmethod
    def validate_implementation(cls, instance) -> bool:
        """
        Validate that instance properly implements the strategy interface.
        
        Args:
            instance: Strategy instance to validate
            
        Returns:
            True if instance properly implements all required methods
            
        Raises:
            TypeError: If instance doesn't implement required methods
        """
        if not isinstance(instance, cls):
            raise TypeError(f"Instance {type(instance)} is not a subclass of {cls}")
        
        # Additional runtime validation could be added here
        # For example, checking method signatures match expected patterns
        return True


class AbstractVectorStrategy(ABC):
    """
    Abstract base class implementing VectorStorageStrategy protocol.
    
    Ensures all vector storage implementations maintain consistent interfaces
    and helps detect breaking changes in the contract.
    """
    
    @abstractmethod
    async def store_runbook_embedding(self, runbook_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Store runbook with vector embedding."""
        pass
    
    @abstractmethod
    async def search_similar_runbooks(self, query: str, limit: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Semantic search for similar runbooks."""
        pass
    
    @abstractmethod
    async def update_runbook_embedding(self, runbook_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Update existing runbook embedding."""
        pass
    
    @abstractmethod
    async def delete_runbook_embedding(self, runbook_id: str) -> bool:
        """Delete runbook from vector store."""
        pass
    
    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector store collection statistics."""
        pass
    
    @abstractmethod
    async def list_stored_runbooks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all stored runbooks with pagination."""
        pass
    
    async def health_check(self) -> bool:
        """
        Default health check implementation with validation.
        
        Returns:
            True if vector storage is healthy and operational
            
        Note:
            Concrete implementations should override to check actual vector DB connectivity.
        """
        return True
    
    def __init_subclass__(cls, **kwargs):
        """Validate subclass implementation completeness (Python 2025 best practice)."""
        super().__init_subclass__(**kwargs)
        # Check if there are any abstract methods left unimplemented
        if hasattr(cls, '__abstractmethods__') and cls.__abstractmethods__:
            import logging
            logger = logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
            logger.debug(f"Abstract vector methods pending implementation: {cls.__abstractmethods__}")
    
    @classmethod
    def validate_implementation(cls, instance) -> bool:
        """Validate vector strategy instance implementation."""
        if not isinstance(instance, cls):
            raise TypeError(f"Instance {type(instance)} is not a subclass of {cls}")
        return True


class AbstractPersistenceStrategy(ABC):
    """
    Abstract base class implementing DataPersistenceStrategy protocol.
    
    Provides explicit contract validation for data persistence operations
    and incident management functionality.
    """
    
    @abstractmethod
    async def save_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """Track runbook usage for effectiveness metrics."""
        pass
    
    @abstractmethod
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """Retrieve usage and effectiveness metrics."""
        pass
    
    @abstractmethod
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> str:
        """Create incident ticket linked to runbook usage."""
        pass
    
    @abstractmethod
    async def update_ticket_status(self, ticket_id: str, status: str, comment: Optional[str] = None) -> bool:
        """Update incident ticket with runbook execution results."""
        pass
    
    @abstractmethod
    async def get_incident_history(self, incident_id: str) -> Dict[str, Any]:
        """Get complete incident history including runbook usage."""
        pass
    
    @abstractmethod
    async def track_runbook_effectiveness(self, runbook_id: str, incident_id: str, success: bool, 
                                        resolution_time: float, notes: Optional[str] = None) -> bool:
        """Track runbook effectiveness for continuous improvement."""
        pass
    
    async def health_check(self) -> bool:
        """
        Default health check implementation with validation.
        
        Returns:
            True if persistence layer is healthy and operational
            
        Note:
            Concrete implementations should override to check actual persistence connectivity.
        """
        return True
    
    def __init_subclass__(cls, **kwargs):
        """Validate subclass implementation completeness (Python 2025 best practice)."""
        super().__init_subclass__(**kwargs)
        # Check if there are any abstract methods left unimplemented
        if hasattr(cls, '__abstractmethods__') and cls.__abstractmethods__:
            import logging
            logger = logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
            logger.debug(f"Abstract persistence methods pending implementation: {cls.__abstractmethods__}")
    
    @classmethod
    def validate_implementation(cls, instance) -> bool:
        """Validate persistence strategy instance implementation."""
        if not isinstance(instance, cls):
            raise TypeError(f"Instance {type(instance)} is not a subclass of {cls}")
        return True


class AbstractNotificationStrategy(ABC):
    """
    Abstract base class implementing NotificationStrategy protocol.
    
    Ensures consistent notification and communication interfaces across
    all implementation tiers (Real, Working, Mock).
    """
    
    @abstractmethod
    async def send_runbook_notification(self, channel: str, runbook_id: str, context: Dict[str, Any]) -> str:
        """Send runbook discovery notification."""
        pass
    
    @abstractmethod
    async def create_approval_thread(self, channel: str, runbook_id: str, context: Dict[str, Any]) -> str:
        """Create interactive approval thread for runbook execution."""
        pass
    
    @abstractmethod
    async def update_thread_status(self, thread_id: str, status: str, results: Dict[str, Any]) -> bool:
        """Update thread with execution status and results."""
        pass
    
    @abstractmethod
    async def send_completion_summary(self, channel: str, summary: Dict[str, Any]) -> str:
        """Send workflow completion summary."""
        pass
    
    @abstractmethod
    async def send_escalation_alert(self, channel: str, incident_id: str, escalation_context: Dict[str, Any]) -> str:
        """Send escalation alert when runbook execution fails."""
        pass
    
    @abstractmethod
    async def create_thread(self, channel: str, message: str, formatting: Optional[Any] = None) -> str:
        """Create new communication thread."""
        pass
    
    @abstractmethod
    async def send_message(self, thread_id: str, message: str, formatting: Optional[Any] = None) -> str:
        """Send message to existing thread."""
        pass
    
    async def health_check(self) -> bool:
        """
        Default health check implementation with validation.
        
        Returns:
            True if notification system is healthy and operational
            
        Note:
            Concrete implementations should override to check actual notification connectivity.
        """
        return True
    
    def __init_subclass__(cls, **kwargs):
        """Validate subclass implementation completeness (Python 2025 best practice)."""
        super().__init_subclass__(**kwargs)
        # Check if there are any abstract methods left unimplemented
        if hasattr(cls, '__abstractmethods__') and cls.__abstractmethods__:
            import logging
            logger = logging.getLogger(f"{cls.__module__}.{cls.__qualname__}")
            logger.debug(f"Abstract notification methods pending implementation: {cls.__abstractmethods__}")
    
    @classmethod
    def validate_implementation(cls, instance) -> bool:
        """Validate notification strategy instance implementation."""
        if not isinstance(instance, cls):
            raise TypeError(f"Instance {type(instance)} is not a subclass of {cls}")
        return True