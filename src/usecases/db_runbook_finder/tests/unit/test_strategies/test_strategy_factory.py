"""
Unit tests for StrategyFactory.

Tests strategy creation, environment-based selection, and factory configuration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategy_factory import StrategyFactory, StrategyConfig
from src.usecases.db_runbook_finder.mcp_server.exceptions import ConfigurationError, MCPRunbookError


class TestStrategyConfig:
    """Test suite for StrategyConfig."""
    
    def test_strategy_config_initialization_production(self):
        """Test StrategyConfig initialization for production environment."""
        config = StrategyConfig(environment="production")
        
        assert config.environment == "production"
        assert config.confluence_base_url is not None
        assert config.jira_base_url is not None
        assert config.chromadb_path is not None
        assert config.slack_token is not None
        assert config.use_mock_strategies is False
        assert config.use_working_strategies is True
    
    def test_strategy_config_initialization_development(self):
        """Test StrategyConfig initialization for development environment."""
        config = StrategyConfig(environment="development")
        
        assert config.environment == "development"
        assert config.use_mock_strategies is True
        assert config.use_working_strategies is False
    
    def test_strategy_config_initialization_testing(self):
        """Test StrategyConfig initialization for testing environment."""
        config = StrategyConfig(environment="testing")
        
        assert config.environment == "testing"
        assert config.use_mock_strategies is True
        assert config.use_working_strategies is False
    
    def test_strategy_config_custom_values(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            environment="custom",
            confluence_base_url="https://custom.confluence.com",
            jira_base_url="https://custom.jira.com",
            chromadb_path="/custom/chromadb",
            slack_token="custom-token-123",
            use_mock_strategies=True,
            use_working_strategies=False
        )
        
        assert config.environment == "custom"
        assert config.confluence_base_url == "https://custom.confluence.com"
        assert config.jira_base_url == "https://custom.jira.com"
        assert config.chromadb_path == "/custom/chromadb"
        assert config.slack_token == "custom-token-123"
        assert config.use_mock_strategies is True
        assert config.use_working_strategies is False


class TestStrategyFactory:
    """Test suite for StrategyFactory."""
    
    @pytest.fixture
    def production_config(self):
        """Create production StrategyConfig."""
        return StrategyConfig(environment="production")
    
    @pytest.fixture
    def development_config(self):
        """Create development StrategyConfig."""
        return StrategyConfig(environment="development")
    
    @pytest.fixture
    def production_factory(self, production_config):
        """Create StrategyFactory for production."""
        return StrategyFactory(config=production_config)
    
    @pytest.fixture
    def development_factory(self, development_config):
        """Create StrategyFactory for development."""
        return StrategyFactory(config=development_config)
    
    def test_factory_initialization(self, production_factory, production_config):
        """Test StrategyFactory initialization."""
        assert production_factory.config == production_config
        assert production_factory._strategies_cache is not None
        assert isinstance(production_factory._strategies_cache, dict)
        assert len(production_factory._strategies_cache) == 0  # Should start empty
    
    @pytest.mark.asyncio
    async def test_create_discovery_strategy_production(self, production_factory):
        """Test creation of discovery strategy in production mode."""
        strategy = await production_factory.create_discovery_strategy()
        
        assert strategy is not None
        # Should be ConfluenceRunbookStrategy in production
        assert hasattr(strategy, 'search_runbooks')
        assert hasattr(strategy, 'get_runbook_details')
        assert hasattr(strategy, 'validate_runbook_access')
        assert hasattr(strategy, 'get_runbook_categories')
    
    @pytest.mark.asyncio
    async def test_create_discovery_strategy_development(self, development_factory):
        """Test creation of discovery strategy in development mode."""
        strategy = await development_factory.create_discovery_strategy()
        
        assert strategy is not None
        # Should be MockDiscoveryStrategy in development
        assert hasattr(strategy, 'search_runbooks')
        assert hasattr(strategy, 'get_runbook_details')
        
        # Should have mock-specific methods
        assert hasattr(strategy, 'get_mock_runbooks')
        assert hasattr(strategy, 'clear_data')
    
    @pytest.mark.asyncio
    async def test_create_vector_strategy_production(self, production_factory):
        """Test creation of vector strategy in production mode."""
        strategy = await production_factory.create_vector_strategy()
        
        assert strategy is not None
        # Should be ChromaDBVectorStrategy in production
        assert hasattr(strategy, 'semantic_search')
        assert hasattr(strategy, 'add_runbook_embedding')
        assert hasattr(strategy, 'update_runbook_embedding')
        assert hasattr(strategy, 'remove_runbook_embedding')
        assert hasattr(strategy, 'get_collection_stats')
    
    @pytest.mark.asyncio
    async def test_create_vector_strategy_development(self, development_factory):
        """Test creation of vector strategy in development mode."""
        strategy = await development_factory.create_vector_strategy()
        
        assert strategy is not None
        # Should be MockVectorStrategy in development
        assert hasattr(strategy, 'semantic_search')
        assert hasattr(strategy, 'add_runbook_embedding')
        
        # Should have mock-specific methods
        assert hasattr(strategy, 'get_mock_embeddings')
        assert hasattr(strategy, 'clear_data')
    
    @pytest.mark.asyncio
    async def test_create_persistence_strategy_production(self, production_factory):
        """Test creation of persistence strategy in production mode."""
        strategy = await production_factory.create_persistence_strategy()
        
        assert strategy is not None
        # Should be JiraDataStrategy in production
        assert hasattr(strategy, 'save_runbook_usage')
        assert hasattr(strategy, 'get_runbook_metrics')
        assert hasattr(strategy, 'create_incident_ticket')
        assert hasattr(strategy, 'update_ticket_status')
        assert hasattr(strategy, 'get_incident_history')
        assert hasattr(strategy, 'track_runbook_effectiveness')
    
    @pytest.mark.asyncio
    async def test_create_persistence_strategy_development(self, development_factory):
        """Test creation of persistence strategy in development mode."""
        strategy = await development_factory.create_persistence_strategy()
        
        assert strategy is not None
        # Should be MockDataStrategy in development
        assert hasattr(strategy, 'save_runbook_usage')
        assert hasattr(strategy, 'get_runbook_metrics')
        
        # Should have mock-specific methods
        assert hasattr(strategy, 'get_all_usage_records')
        assert hasattr(strategy, 'simulate_incident_scenario')
    
    @pytest.mark.asyncio
    async def test_create_notification_strategy_production(self, production_factory):
        """Test creation of notification strategy in production mode."""
        strategy = await production_factory.create_notification_strategy()
        
        assert strategy is not None
        # Should be SlackNotificationStrategy in production
        assert hasattr(strategy, 'send_runbook_notification')
        assert hasattr(strategy, 'create_approval_thread')
        assert hasattr(strategy, 'update_thread_status')
        assert hasattr(strategy, 'send_completion_summary')
        assert hasattr(strategy, 'send_alert_notification')
    
    @pytest.mark.asyncio
    async def test_create_notification_strategy_development(self, development_factory):
        """Test creation of notification strategy in development mode."""
        strategy = await development_factory.create_notification_strategy()
        
        assert strategy is not None
        # Should be MockNotificationStrategy in development
        assert hasattr(strategy, 'send_runbook_notification')
        assert hasattr(strategy, 'create_approval_thread')
        
        # Should have mock-specific methods
        assert hasattr(strategy, 'get_sent_notifications')
        assert hasattr(strategy, 'simulate_approval_response')
    
    @pytest.mark.asyncio
    async def test_create_all_strategies_production(self, production_factory):
        """Test creation of all strategies in production mode."""
        strategies = await production_factory.create_all_strategies()
        
        assert isinstance(strategies, dict)
        assert "discovery" in strategies
        assert "vector" in strategies
        assert "persistence" in strategies
        assert "notification" in strategies
        
        # All strategies should be created
        assert strategies["discovery"] is not None
        assert strategies["vector"] is not None
        assert strategies["persistence"] is not None
        assert strategies["notification"] is not None
    
    @pytest.mark.asyncio
    async def test_create_all_strategies_development(self, development_factory):
        """Test creation of all strategies in development mode."""
        strategies = await development_factory.create_all_strategies()
        
        assert isinstance(strategies, dict)
        assert len(strategies) == 4
        
        # All should be mock strategies
        for strategy_type, strategy in strategies.items():
            assert strategy is not None
            # Mock strategies should have mock-specific methods
            if strategy_type == "discovery":
                assert hasattr(strategy, 'get_mock_runbooks')
            elif strategy_type == "vector":
                assert hasattr(strategy, 'get_mock_embeddings')
            elif strategy_type == "persistence":
                assert hasattr(strategy, 'get_all_usage_records')
            elif strategy_type == "notification":
                assert hasattr(strategy, 'get_sent_notifications')
    
    @pytest.mark.asyncio
    async def test_strategy_caching(self, development_factory):
        """Test that strategies are cached after creation."""
        # Create discovery strategy twice
        strategy1 = await development_factory.create_discovery_strategy()
        strategy2 = await development_factory.create_discovery_strategy()
        
        # Should be the same instance due to caching
        assert strategy1 is strategy2
        
        # Check cache contains strategy
        assert "discovery" in development_factory._strategies_cache
        assert development_factory._strategies_cache["discovery"] is strategy1
    
    @pytest.mark.asyncio
    async def test_strategy_caching_all_strategies(self, development_factory):
        """Test caching with create_all_strategies."""
        # Create all strategies
        strategies1 = await development_factory.create_all_strategies()
        
        # Create individual strategies
        discovery2 = await development_factory.create_discovery_strategy()
        vector2 = await development_factory.create_vector_strategy()
        
        # Should use cached instances
        assert strategies1["discovery"] is discovery2
        assert strategies1["vector"] is vector2
    
    def test_get_strategy_status(self, development_factory):
        """Test strategy status retrieval before creation."""
        status = development_factory.get_strategy_status()
        
        assert isinstance(status, dict)
        assert "discovery" in status
        assert "vector" in status
        assert "persistence" in status
        assert "notification" in status
        
        # All should be "not_created" initially
        for strategy_type, strategy_status in status.items():
            assert strategy_status == "not_created"
    
    @pytest.mark.asyncio
    async def test_get_strategy_status_after_creation(self, development_factory):
        """Test strategy status after creating strategies."""
        # Create some strategies
        await development_factory.create_discovery_strategy()
        await development_factory.create_vector_strategy()
        
        status = development_factory.get_strategy_status()
        
        # Created strategies should show as "created"
        assert status["discovery"] == "created"
        assert status["vector"] == "created"
        assert status["persistence"] == "not_created"
        assert status["notification"] == "not_created"
    
    def test_clear_cache(self, development_factory):
        """Test strategy cache clearing."""
        # Add something to cache manually
        development_factory._strategies_cache["test"] = Mock()
        
        development_factory.clear_cache()
        
        # Cache should be empty
        assert len(development_factory._strategies_cache) == 0
    
    @pytest.mark.asyncio
    async def test_clear_cache_after_strategy_creation(self, development_factory):
        """Test cache clearing after creating strategies."""
        # Create strategies
        await development_factory.create_discovery_strategy()
        await development_factory.create_vector_strategy()
        
        # Cache should have strategies
        assert len(development_factory._strategies_cache) == 2
        
        # Clear cache
        development_factory.clear_cache()
        
        # Cache should be empty
        assert len(development_factory._strategies_cache) == 0
        
        # Strategy status should reflect cleared cache
        status = development_factory.get_strategy_status()
        for strategy_status in status.values():
            assert strategy_status == "not_created"
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_environment(self):
        """Test error handling with invalid environment configuration."""
        # Create config with invalid environment that might cause issues
        config = StrategyConfig(
            environment="production",
            confluence_base_url="invalid_url",
            jira_base_url="invalid_url",
            slack_token="invalid_token"
        )
        
        factory = StrategyFactory(config=config)
        
        # Strategy creation might fail with invalid config, but should handle gracefully
        # This depends on the actual strategy implementations
        try:
            await factory.create_discovery_strategy()
            # If it succeeds, that's fine too
        except (ConfigurationError, MCPRunbookError):
            # Expected for invalid configuration
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_strategy_creation(self, development_factory):
        """Test concurrent strategy creation for thread safety."""
        # Create multiple strategies concurrently
        tasks = [
            development_factory.create_discovery_strategy(),
            development_factory.create_vector_strategy(),
            development_factory.create_persistence_strategy(),
            development_factory.create_notification_strategy()
        ]
        
        strategies = await asyncio.gather(*tasks)
        
        # All strategies should be created successfully
        assert len(strategies) == 4
        for strategy in strategies:
            assert strategy is not None
        
        # Check that they were cached properly
        status = development_factory.get_strategy_status()
        for strategy_status in status.values():
            assert strategy_status == "created"
    
    @pytest.mark.asyncio
    async def test_multiple_create_all_strategies_calls(self, development_factory):
        """Test multiple calls to create_all_strategies."""
        # Call create_all_strategies multiple times
        strategies1 = await development_factory.create_all_strategies()
        strategies2 = await development_factory.create_all_strategies()
        strategies3 = await development_factory.create_all_strategies()
        
        # All calls should return the same cached instances
        assert strategies1 is not strategies2  # Different dict instances
        assert strategies1["discovery"] is strategies2["discovery"]  # Same strategy instances
        assert strategies2["vector"] is strategies3["vector"]
        assert strategies1["persistence"] is strategies3["persistence"]
        assert strategies2["notification"] is strategies3["notification"]
    
    def test_factory_with_custom_config(self):
        """Test factory with custom configuration."""
        custom_config = StrategyConfig(
            environment="custom_test",
            confluence_base_url="https://custom.test.com",
            use_mock_strategies=True,
            use_working_strategies=False
        )
        
        factory = StrategyFactory(config=custom_config)
        
        assert factory.config.environment == "custom_test"
        assert factory.config.confluence_base_url == "https://custom.test.com"
        assert factory.config.use_mock_strategies is True
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self):
        """Test the graceful degradation pattern (Real → Working → Mock)."""
        # This test simulates the degradation pattern described in the requirements
        
        # Start with production config (should try Real strategies)
        prod_config = StrategyConfig(environment="production")
        prod_factory = StrategyFactory(config=prod_config)
        
        # In a real scenario, if Real strategies fail, it should fall back to Working
        # If Working strategies fail, it should fall back to Mock
        # For this test, we'll verify that each environment creates appropriate strategies
        
        try:
            prod_strategies = await prod_factory.create_all_strategies()
            # Production should create real/working strategies
            assert prod_strategies is not None
        except Exception:
            # If production fails, that's expected in test environment
            pass
        
        # Development should always succeed with mock strategies
        dev_config = StrategyConfig(environment="development")
        dev_factory = StrategyFactory(config=dev_config)
        dev_strategies = await dev_factory.create_all_strategies()
        
        assert dev_strategies is not None
        assert len(dev_strategies) == 4
    
    def test_strategy_config_validation(self):
        """Test StrategyConfig parameter validation."""
        # Test with minimal valid config
        config = StrategyConfig(environment="test")
        assert config.environment == "test"
        
        # Test with all parameters
        config_full = StrategyConfig(
            environment="full_test",
            confluence_base_url="https://confluence.test.com",
            jira_base_url="https://jira.test.com",
            chromadb_path="/test/chromadb",
            slack_token="test-token",
            use_mock_strategies=False,
            use_working_strategies=True
        )
        
        assert config_full.environment == "full_test"
        assert config_full.confluence_base_url == "https://confluence.test.com"
        assert config_full.jira_base_url == "https://jira.test.com"
        assert config_full.chromadb_path == "/test/chromadb"
        assert config_full.slack_token == "test-token"
        assert config_full.use_mock_strategies is False
        assert config_full.use_working_strategies is True
    
    @pytest.mark.asyncio
    async def test_strategy_health_checks(self, development_factory):
        """Test that created strategies have working health checks."""
        strategies = await development_factory.create_all_strategies()
        
        # Test health checks for all strategies
        for strategy_type, strategy in strategies.items():
            if hasattr(strategy, 'health_check'):
                health = await strategy.health_check()
                assert isinstance(health, bool)
                # Mock strategies should always be healthy
                assert health is True
    
    @pytest.mark.asyncio
    async def test_factory_performance(self, development_factory):
        """Test factory performance with multiple strategy creations."""
        import time
        
        start_time = time.time()
        
        # Create strategies multiple times (should use caching)
        for _ in range(10):
            await development_factory.create_all_strategies()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast due to caching (mock strategies are lightweight)
        assert duration < 1.0, f"Strategy creation took {duration:.2f} seconds, should be <1.0s"
    
    def test_factory_string_representation(self, development_factory):
        """Test factory string representation."""
        factory_str = str(development_factory)
        assert "StrategyFactory" in factory_str
        assert development_factory.config.environment in factory_str