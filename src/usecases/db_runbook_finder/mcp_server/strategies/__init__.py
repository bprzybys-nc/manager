"""
Strategy implementations for the RunbookRepositoryMCP Server.

This package contains all Abstract Base Class interfaces and their concrete
implementations for the quadruple strategy pattern architecture.
"""

from .protocols import (
    AbstractDiscoveryStrategy,
    AbstractVectorStrategy,
    AbstractPersistenceStrategy,
    AbstractNotificationStrategy
)

__all__ = [
    "AbstractDiscoveryStrategy",
    "AbstractVectorStrategy", 
    "AbstractPersistenceStrategy",
    "AbstractNotificationStrategy"
]