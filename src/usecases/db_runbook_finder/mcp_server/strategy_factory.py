"""
Strategy Factory Implementation.

This module provides the StrategyFactory for environment-based strategy selection,
implementing the Real → Working → Mock hierarchy for graceful degradation.
"""

import logging
import os
from typing import Dict, Any, Optional, Union
from enum import Enum

from .strategies.protocols import (
    AbstractDiscoveryStrategy,
    AbstractVectorStrategy,
    AbstractPersistenceStrategy,
    AbstractNotificationStrategy
)

# Real implementations
from .strategies.confluence_discovery import ConfluenceRunbookStrategy
from .strategies.chromadb_vector import ChromaDBVectorStrategy
from .strategies.jira_persistence import JiraPersistenceStrategy
from .strategies.slack_notification import SlackNotificationStrategy

logger = logging.getLogger(__name__)


class ImplementationTier(Enum):
    """Implementation tier levels for graceful degradation."""
    REAL = "real"      # Full external service integration
    WORKING = "working"  # Functional with limited features
    MOCK = "mock"      # Test/development implementation


class StrategyConfig:
    """Configuration for strategy selection and initialization."""
    
    def __init__(self, environment: str = "development"):
        """
        Initialize strategy configuration.
        
        Args:
            environment: Target environment (production, staging, development, test)
        """
        self.environment = environment
        self.confluence_url = os.getenv("CONFLUENCE_TOOL_URL", "http://localhost:8000")
        self.jira_url = os.getenv("JIRA_TOOL_URL", "http://localhost:8001") 
        self.slack_url = os.getenv("SLACK_TOOL_URL", "http://localhost:8002")
        self.timeout = int(os.getenv("STRATEGY_TIMEOUT", "30"))
        
        # Environment-based tier preferences
        self.tier_preferences = {
            "production": [ImplementationTier.REAL, ImplementationTier.WORKING],
            "staging": [ImplementationTier.REAL, ImplementationTier.WORKING, ImplementationTier.MOCK],
            "development": [ImplementationTier.WORKING, ImplementationTier.MOCK, ImplementationTier.REAL],
            "test": [ImplementationTier.MOCK, ImplementationTier.WORKING]
        }
        
        logger.info(f"StrategyConfig initialized for environment: {environment}")
    
    def get_preferred_tiers(self) -> list[ImplementationTier]:
        """Get preferred implementation tiers for current environment."""
        return self.tier_preferences.get(self.environment, [ImplementationTier.MOCK])


class StrategyFactory:
    """
    Factory for creating strategy implementations with graceful degradation.
    
    Implements Real → Working → Mock hierarchy based on environment configuration
    and service availability checks.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        Initialize strategy factory.
        
        Args:
            config: Strategy configuration (auto-detected if None)
        """
        self.config = config or StrategyConfig(
            environment=os.getenv("ENVIRONMENT", "development")
        )
        
        # Strategy availability cache
        self._availability_cache: Dict[str, Dict[ImplementationTier, bool]] = {
            "discovery": {},
            "vector": {},
            "persistence": {},
            "notification": {}
        }
        
        # Cache timeout in seconds
        self._cache_timeout = int(os.getenv("STRATEGY_CACHE_TIMEOUT", "300"))  # 5 minutes
        self._last_check: Dict[str, float] = {}
        
        logger.info(f"StrategyFactory initialized for {self.config.environment} environment")
    
    async def create_discovery_strategy(self) -> AbstractDiscoveryStrategy:
        """
        Create runbook discovery strategy with graceful degradation.
        
        Returns:
            Best available discovery strategy implementation
        """
        strategy_type = "discovery"
        
        for tier in self.config.get_preferred_tiers():
            try:
                if tier == ImplementationTier.REAL:
                    if await self._check_service_availability("confluence", self.config.confluence_url):
                        strategy = ConfluenceRunbookStrategy(
                            base_url=self.config.confluence_url,
                            timeout=self.config.timeout
                        )
                        if await strategy.health_check():
                            logger.info(f"Created REAL discovery strategy: ConfluenceRunbookStrategy")
                            return strategy
                        else:
                            await strategy.close()
                            
                elif tier == ImplementationTier.WORKING:
                    # Working implementation would be a simplified Confluence strategy
                    # or a hybrid approach with cached data
                    strategy = ConfluenceRunbookStrategy(
                        base_url=self.config.confluence_url,
                        timeout=self.config.timeout
                    )
                    # For working tier, we're more lenient on health checks
                    logger.info(f"Created WORKING discovery strategy: ConfluenceRunbookStrategy")
                    return strategy
                    
                elif tier == ImplementationTier.MOCK:
                    from .strategies.mock_discovery import MockDiscoveryStrategy
                    strategy = MockDiscoveryStrategy()
                    logger.info(f"Created MOCK discovery strategy: MockDiscoveryStrategy")
                    return strategy
                    
            except Exception as e:
                logger.warning(f"Failed to create {tier.value} discovery strategy: {e}")
                continue
        
        # Fallback to mock if all else fails
        try:
            from .strategies.mock_discovery import MockDiscoveryStrategy
            strategy = MockDiscoveryStrategy()
            logger.warning("All discovery strategies failed, falling back to MockDiscoveryStrategy")
            return strategy
        except ImportError:
            logger.error("Mock strategy not available, using basic ConfluenceRunbookStrategy")
            return ConfluenceRunbookStrategy(
                base_url=self.config.confluence_url,
                timeout=self.config.timeout
            )
    
    async def create_vector_strategy(self) -> AbstractVectorStrategy:
        """
        Create vector storage strategy with graceful degradation.
        
        Returns:
            Best available vector storage strategy implementation
        """
        strategy_type = "vector"
        
        for tier in self.config.get_preferred_tiers():
            try:
                if tier == ImplementationTier.REAL:
                    if await self._check_service_availability("confluence", self.config.confluence_url):
                        strategy = ChromaDBVectorStrategy(
                            base_url=self.config.confluence_url,
                            timeout=self.config.timeout
                        )
                        if await strategy.health_check():
                            logger.info(f"Created REAL vector strategy: ChromaDBVectorStrategy")
                            return strategy
                        else:
                            await strategy.close()
                            
                elif tier == ImplementationTier.WORKING:
                    # Working implementation with fallback mechanisms
                    strategy = ChromaDBVectorStrategy(
                        base_url=self.config.confluence_url,
                        timeout=self.config.timeout
                    )
                    logger.info(f"Created WORKING vector strategy: ChromaDBVectorStrategy")
                    return strategy
                    
                elif tier == ImplementationTier.MOCK:
                    from .strategies.mock_vector import MockVectorStrategy
                    strategy = MockVectorStrategy()
                    logger.info(f"Created MOCK vector strategy: MockVectorStrategy")
                    return strategy
                    
            except Exception as e:
                logger.warning(f"Failed to create {tier.value} vector strategy: {e}")
                continue
        
        # Fallback to mock
        try:
            from .strategies.mock_vector import MockVectorStrategy
            strategy = MockVectorStrategy()
            logger.warning("All vector strategies failed, falling back to MockVectorStrategy")
            return strategy
        except ImportError:
            logger.error("Mock strategy not available, using basic ChromaDBVectorStrategy")
            return ChromaDBVectorStrategy(
                base_url=self.config.confluence_url,
                timeout=self.config.timeout
            )
    
    async def create_persistence_strategy(self) -> AbstractPersistenceStrategy:
        """
        Create data persistence strategy with graceful degradation.
        
        Returns:
            Best available persistence strategy implementation
        """
        strategy_type = "persistence"
        
        for tier in self.config.get_preferred_tiers():
            try:
                if tier == ImplementationTier.REAL:
                    if await self._check_service_availability("jira", self.config.jira_url):
                        strategy = JiraPersistenceStrategy(
                            base_url=self.config.jira_url,
                            timeout=self.config.timeout
                        )
                        if await strategy.health_check():
                            logger.info(f"Created REAL persistence strategy: JiraPersistenceStrategy")
                            return strategy
                        else:
                            await strategy.close()
                            
                elif tier == ImplementationTier.WORKING:
                    # Working implementation with in-memory fallbacks
                    strategy = JiraPersistenceStrategy(
                        base_url=self.config.jira_url,
                        timeout=self.config.timeout
                    )
                    logger.info(f"Created WORKING persistence strategy: JiraPersistenceStrategy")
                    return strategy
                    
                elif tier == ImplementationTier.MOCK:
                    from .strategies.mock_persistence import MockPersistenceStrategy
                    strategy = MockPersistenceStrategy()
                    logger.info(f"Created MOCK persistence strategy: MockPersistenceStrategy")
                    return strategy
                    
            except Exception as e:
                logger.warning(f"Failed to create {tier.value} persistence strategy: {e}")
                continue
        
        # Fallback to mock
        try:
            from .strategies.mock_persistence import MockPersistenceStrategy
            strategy = MockPersistenceStrategy()
            logger.warning("All persistence strategies failed, falling back to MockPersistenceStrategy")
            return strategy
        except ImportError:
            logger.error("Mock strategy not available, using basic JiraPersistenceStrategy")
            return JiraPersistenceStrategy(
                base_url=self.config.jira_url,
                timeout=self.config.timeout
            )
    
    async def create_notification_strategy(self) -> AbstractNotificationStrategy:
        """
        Create notification strategy with graceful degradation.
        
        Returns:
            Best available notification strategy implementation
        """
        strategy_type = "notification"
        
        for tier in self.config.get_preferred_tiers():
            try:
                if tier == ImplementationTier.REAL:
                    if await self._check_service_availability("slack", self.config.slack_url):
                        strategy = SlackNotificationStrategy(
                            base_url=self.config.slack_url,
                            timeout=self.config.timeout
                        )
                        if await strategy.health_check():
                            logger.info(f"Created REAL notification strategy: SlackNotificationStrategy")
                            return strategy
                        else:
                            await strategy.close()
                            
                elif tier == ImplementationTier.WORKING:
                    # Working implementation with basic messaging
                    strategy = SlackNotificationStrategy(
                        base_url=self.config.slack_url,
                        timeout=self.config.timeout
                    )
                    logger.info(f"Created WORKING notification strategy: SlackNotificationStrategy")
                    return strategy
                    
                elif tier == ImplementationTier.MOCK:
                    from .strategies.mock_notification import MockNotificationStrategy
                    strategy = MockNotificationStrategy()
                    logger.info(f"Created MOCK notification strategy: MockNotificationStrategy")
                    return strategy
                    
            except Exception as e:
                logger.warning(f"Failed to create {tier.value} notification strategy: {e}")
                continue
        
        # Fallback to mock
        try:
            from .strategies.mock_notification import MockNotificationStrategy
            strategy = MockNotificationStrategy()
            logger.warning("All notification strategies failed, falling back to MockNotificationStrategy")
            return strategy
        except ImportError:
            logger.error("Mock strategy not available, using basic SlackNotificationStrategy")
            return SlackNotificationStrategy(
                base_url=self.config.slack_url,
                timeout=self.config.timeout
            )
    
    async def create_all_strategies(self) -> Dict[str, Any]:
        """
        Create all strategies using optimal implementations.
        
        Returns:
            Dictionary containing all strategy instances
        """
        logger.info("Creating all strategies with graceful degradation...")
        
        strategies = {
            "discovery": await self.create_discovery_strategy(),
            "vector": await self.create_vector_strategy(), 
            "persistence": await self.create_persistence_strategy(),
            "notification": await self.create_notification_strategy()
        }
        
        # Log final strategy configuration
        strategy_summary = {
            name: type(strategy).__name__
            for name, strategy in strategies.items()
        }
        logger.info(f"Strategy selection complete: {strategy_summary}")
        
        return strategies
    
    async def _check_service_availability(self, service_name: str, url: str) -> bool:
        """
        Check if external service is available.
        
        Args:
            service_name: Service name for caching
            url: Service URL to check
            
        Returns:
            True if service is available
        """
        import time
        import httpx
        
        # Check cache first
        cache_key = f"{service_name}_{url}"
        current_time = time.time()
        
        if (cache_key in self._last_check and 
            current_time - self._last_check[cache_key] < self._cache_timeout):
            cached_result = self._availability_cache.get(service_name, {}).get(ImplementationTier.REAL)
            if cached_result is not None:
                return cached_result
        
        # Perform availability check
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                available = response.status_code == 200
                
                # Update cache
                if service_name not in self._availability_cache:
                    self._availability_cache[service_name] = {}
                self._availability_cache[service_name][ImplementationTier.REAL] = available
                self._last_check[cache_key] = current_time
                
                logger.debug(f"Service {service_name} availability: {available}")
                return available
                
        except Exception as e:
            logger.debug(f"Service {service_name} unavailable: {e}")
            
            # Update cache with failure
            if service_name not in self._availability_cache:
                self._availability_cache[service_name] = {}
            self._availability_cache[service_name][ImplementationTier.REAL] = False
            self._last_check[cache_key] = current_time
            
            return False
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get current strategy availability status.
        
        Returns:
            Status dictionary with availability information
        """
        return {
            "environment": self.config.environment,
            "preferred_tiers": [tier.value for tier in self.config.get_preferred_tiers()],
            "service_urls": {
                "confluence": self.config.confluence_url,
                "jira": self.config.jira_url,
                "slack": self.config.slack_url
            },
            "availability_cache": {
                service: {tier.value: status for tier, status in tiers.items()}
                for service, tiers in self._availability_cache.items()
            },
            "cache_timeout": self._cache_timeout
        }
    
    async def refresh_availability_cache(self) -> None:
        """Refresh service availability cache."""
        logger.info("Refreshing service availability cache...")
        
        services = [
            ("confluence", self.config.confluence_url),
            ("jira", self.config.jira_url),
            ("slack", self.config.slack_url)
        ]
        
        for service_name, url in services:
            await self._check_service_availability(service_name, url)
        
        logger.info("Service availability cache refreshed")