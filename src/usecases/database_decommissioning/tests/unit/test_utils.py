"""
Unit tests for database decommissioning utilities.

Tests the utility functions with Manager integration while preserving GraphMCP patterns.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from app.utils import (
    create_logger_for_workflow,
    get_manager_database_client,
    validate_workflow_parameters,
    create_workflow_config,
    format_workflow_summary,
)
from app.models import WorkflowConfig


@pytest.mark.unit
class TestLoggingUtils:
    """Test logging utility functions."""

    def test_create_logger_for_workflow_basic(self, test_workflow_id, postgres_air_database):
        """Test basic logger creation."""
        logger = create_logger_for_workflow(
            test_workflow_id, postgres_air_database
        )
        
        assert logger is not None
        assert hasattr(logger, 'log_info')
        assert hasattr(logger, 'log_error')
        assert hasattr(logger, 'log_warning')

    def test_create_logger_for_workflow_with_tenant(
        self, test_workflow_id, postgres_air_database, test_tenant_id
    ):
        """Test logger creation with tenant context."""
        logger = create_logger_for_workflow(
            test_workflow_id, postgres_air_database, test_tenant_id
        )
        
        assert logger is not None
        # Verify tenant context is included in logger configuration
        assert hasattr(logger, 'log_info')

    def test_logger_methods_available(self, test_workflow_id, postgres_air_database):
        """Test that all required logger methods are available."""
        logger = create_logger_for_workflow(
            test_workflow_id, postgres_air_database
        )
        
        # Test all expected methods exist
        expected_methods = [
            'log_info', 'log_error', 'log_warning',
            'log_workflow_start', 'log_workflow_end',
            'log_step_start', 'log_step_end',
            'log_table'
        ]
        
        for method in expected_methods:
            assert hasattr(logger, method), f"Logger missing method: {method}"


@pytest.mark.unit
@pytest.mark.manager
class TestManagerIntegration:
    """Test Manager-specific integration utilities."""

    @patch('src.config')
    def test_get_manager_database_client_success(self, mock_config):
        """Test successful database client creation."""
        mock_config.MONGO_DB_URI = "mongodb://localhost:27017/test"
        
        with patch('...app.utils.DatabaseClient') as mock_db_client:
            mock_instance = Mock()
            mock_db_client.return_value = mock_instance
            
            client = get_manager_database_client()
            
            assert client is not None
            mock_db_client.assert_called_once()

    @patch('src.config')
    def test_get_manager_database_client_no_uri(self, mock_config):
        """Test database client creation with no URI."""
        mock_config.MONGO_DB_URI = None
        
        client = get_manager_database_client()
        
        assert client is None

    @patch('src.config')
    def test_get_manager_database_client_exception(self, mock_config):
        """Test database client creation with exception."""
        mock_config.MONGO_DB_URI = "mongodb://localhost:27017/test"
        
        with patch('...app.utils.DatabaseClient', side_effect=Exception("Connection error")):
            client = get_manager_database_client()
            
            assert client is None

    def test_create_workflow_state_manager_basic(self, workflow_config):
        """Test basic workflow state manager creation."""
        state_manager = create_workflow_state_manager(workflow_config)
        
        assert state_manager is not None
        assert hasattr(state_manager, 'database_name')
        assert state_manager.database_name == workflow_config.database_name

    def test_create_workflow_state_manager_with_db_client(
        self, workflow_config, mock_database_client
    ):
        """Test state manager creation with database client."""
        state_manager = create_workflow_state_manager(
            workflow_config, mock_database_client
        )
        
        assert state_manager is not None
        assert state_manager.db_client == mock_database_client

    @patch('src.config')
    def test_get_azure_openai_client_success(self, mock_config):
        """Test successful Azure OpenAI client creation."""
        mock_config.AZURE_OPENAI_API_KEY = "test_key"
        mock_config.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        
        with patch('...app.utils.AsyncAzureOpenAI') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            client = get_azure_openai_client()
            
            assert client is not None
            mock_client.assert_called_once()

    @patch('src.config')
    def test_get_azure_openai_client_missing_config(self, mock_config):
        """Test Azure OpenAI client creation with missing config."""
        mock_config.AZURE_OPENAI_API_KEY = None
        mock_config.AZURE_OPENAI_ENDPOINT = None
        
        client = get_azure_openai_client()
        
        assert client is None


@pytest.mark.unit
class TestEnvironmentValidation:
    """Test environment validation utilities."""

    @patch('...app.utils.get_manager_database_client')
    @patch('...app.utils.get_azure_openai_client')
    def test_validate_environment_dependencies_success(
        self, mock_openai_client, mock_db_client
    ):
        """Test successful environment validation."""
        mock_db_client.return_value = Mock()
        mock_openai_client.return_value = Mock()
        
        result = validate_environment_dependencies()
        
        assert result["success"] is True
        assert "database_client" in result["available_services"]
        assert "azure_openai" in result["available_services"]

    @patch('...app.utils.get_manager_database_client')
    @patch('...app.utils.get_azure_openai_client')
    def test_validate_environment_dependencies_partial(
        self, mock_openai_client, mock_db_client
    ):
        """Test partial environment validation."""
        mock_db_client.return_value = None  # Database not available
        mock_openai_client.return_value = Mock()
        
        result = validate_environment_dependencies()
        
        assert result["success"] is False
        assert "azure_openai" in result["available_services"]
        assert "database_client" not in result["available_services"]
        assert len(result["missing_services"]) > 0

    @patch('...app.utils.get_manager_database_client')
    @patch('...app.utils.get_azure_openai_client')
    def test_validate_environment_dependencies_none(
        self, mock_openai_client, mock_db_client
    ):
        """Test environment validation with no services."""
        mock_db_client.return_value = None
        mock_openai_client.return_value = None
        
        result = validate_environment_dependencies()
        
        assert result["success"] is False
        assert len(result["available_services"]) == 0
        assert len(result["missing_services"]) > 0


@pytest.mark.unit
class TestUtilityFunctions:
    """Test general utility functions."""

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        assert format_duration(45.5) == "45.5s"
        assert format_duration(1.0) == "1.0s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        assert format_duration(90.0) == "1m 30s"
        assert format_duration(120.0) == "2m 0s"
        assert format_duration(125.5) == "2m 5s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        assert format_duration(3600.0) == "1h 0m 0s"
        assert format_duration(3665.0) == "1h 1m 5s"
        assert format_duration(7325.5) == "2h 2m 5s"

    def test_format_duration_edge_cases(self):
        """Test duration formatting edge cases."""
        assert format_duration(0.0) == "0.0s"
        assert format_duration(0.1) == "0.1s"

    def test_safe_json_serialize_basic(self):
        """Test basic JSON serialization."""
        data = {"key": "value", "number": 42}
        result = safe_json_serialize(data)
        
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_safe_json_serialize_complex(self):
        """Test JSON serialization with complex objects."""
        from datetime import datetime
        
        data = {
            "timestamp": datetime.now(),
            "path": Path("/test/path"),
            "function": lambda x: x,
        }
        
        result = safe_json_serialize(data)
        
        assert isinstance(result, str)
        # Should handle non-serializable objects gracefully
        assert "timestamp" in result

    def test_safe_json_serialize_exception(self):
        """Test JSON serialization with exception."""
        # Create an object that can't be serialized
        class UnserializableClass:
            def __init__(self):
                self.circular_ref = self
        
        data = {"unserializable": UnserializableClass()}
        
        result = safe_json_serialize(data)
        
        # Should return a safe fallback
        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()

    def test_mask_sensitive_data_basic(self):
        """Test basic sensitive data masking."""
        data = {
            "api_key": "secret123",
            "password": "mypassword",
            "token": "abcdef123456",
            "safe_data": "not_sensitive",
        }
        
        result = mask_sensitive_data(data)
        
        assert result["api_key"] == "***MASKED***"
        assert result["password"] == "***MASKED***"
        assert result["token"] == "***MASKED***"
        assert result["safe_data"] == "not_sensitive"

    def test_mask_sensitive_data_nested(self):
        """Test sensitive data masking in nested structures."""
        data = {
            "config": {
                "database": {
                    "password": "dbpassword",
                    "host": "localhost",
                },
                "api_key": "secret",
            },
            "metadata": {
                "version": "1.0",
            },
        }
        
        result = mask_sensitive_data(data)
        
        assert result["config"]["database"]["password"] == "***MASKED***"
        assert result["config"]["database"]["host"] == "localhost"
        assert result["config"]["api_key"] == "***MASKED***"
        assert result["metadata"]["version"] == "1.0"

    def test_mask_sensitive_data_list(self):
        """Test sensitive data masking in lists."""
        data = {
            "credentials": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "password": "pass2"},
            ],
            "public_info": ["item1", "item2"],
        }
        
        result = mask_sensitive_data(data)
        
        assert result["credentials"][0]["password"] == "***MASKED***"
        assert result["credentials"][1]["password"] == "***MASKED***"
        assert result["credentials"][0]["username"] == "user1"
        assert result["public_info"] == ["item1", "item2"]

    def test_mask_sensitive_data_custom_keys(self):
        """Test sensitive data masking with custom sensitive keys."""
        data = {
            "secret_value": "confidential",
            "auth_token": "token123",
            "public_data": "visible",
        }
        
        custom_keys = ["secret_value", "auth_token"]
        result = mask_sensitive_data(data, sensitive_keys=custom_keys)
        
        assert result["secret_value"] == "***MASKED***"
        assert result["auth_token"] == "***MASKED***"
        assert result["public_data"] == "visible"


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncUtilities:
    """Test async utility functions."""

    async def test_async_utility_placeholder(self):
        """Placeholder for async utility tests."""
        # This is a placeholder for future async utility functions
        # that may be added to the utils module
        assert True


@pytest.mark.unit
@pytest.mark.tenant
class TestTenantAwareUtilities:
    """Test tenant-aware utility functions."""

    def test_create_logger_tenant_context(self, test_workflow_id, postgres_air_database, test_tenant_id):
        """Test logger creation with tenant context."""
        logger = create_logger_for_workflow(
            test_workflow_id, postgres_air_database, test_tenant_id
        )
        
        # Verify logger is created successfully with tenant context
        assert logger is not None
        
        # Test that tenant-specific logging methods work
        try:
            logger.log_info("Test message", {"tenant_id": test_tenant_id})
        except Exception as e:
            pytest.fail(f"Tenant-aware logging failed: {e}")

    def test_state_manager_tenant_awareness(self, test_tenant_id):
        """Test state manager with tenant awareness."""
        config = WorkflowConfig(
            database_name="test_db",
            repo_owner="test_owner",
            repo_name="test_repo",
            tenant_id=test_tenant_id,
        )
        
        state_manager = create_workflow_state_manager(config)
        
        # Verify tenant context is preserved
        assert hasattr(state_manager, 'tenant_id')
        assert state_manager.tenant_id == test_tenant_id


@pytest.mark.unit
@pytest.mark.slow
class TestPerformanceUtilities:
    """Test performance-related utility functions."""

    def test_duration_formatting_performance(self):
        """Test duration formatting performance."""
        import time
        
        # Test that duration formatting is fast
        start_time = time.time()
        
        for i in range(1000):
            format_duration(float(i))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 1000 formatting operations in less than 1 second
        assert execution_time < 1.0

    def test_json_serialization_performance(self):
        """Test JSON serialization performance."""
        import time
        
        # Create a reasonably complex data structure
        data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(100)],
            "metadata": {"timestamp": "2024-01-01", "version": "1.0"},
        }
        
        start_time = time.time()
        
        for _ in range(100):
            safe_json_serialize(data)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 100 serialization operations quickly
        assert execution_time < 1.0