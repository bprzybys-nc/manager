"""
Tests for comprehensive error handling and logging functionality.

This module tests the error handling, retry mechanisms, correlation ID tracking,
and environment validation features.
"""

import os
import time
import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from .error_handler import (
    StructuredLogger,
    RetryConfig,
    with_retry,
    RateLimitError,
    ServiceUnavailableError,
    create_error_response,
    validate_environment_variables,
    ErrorHandler,
    CorrelationIDFilter
)
from .models import ErrorResponse


class TestCorrelationIDFilter:
    """Test correlation ID logging filter."""
    
    def test_filter_adds_correlation_id_when_missing(self):
        """Test that filter adds correlation ID when not present."""
        filter_instance = CorrelationIDFilter()
        filter_instance._correlation_id = "test-correlation-id"
        
        record = Mock()
        # Simulate missing correlation_id attribute
        del record.correlation_id
        
        result = filter_instance.filter(record)
        
        assert result is True
        assert record.correlation_id == "test-correlation-id"
    
    def test_filter_preserves_existing_correlation_id(self):
        """Test that filter preserves existing correlation ID."""
        filter_instance = CorrelationIDFilter()
        filter_instance._correlation_id = "new-correlation-id"
        
        record = Mock()
        record.correlation_id = "existing-correlation-id"
        
        result = filter_instance.filter(record)
        
        assert result is True
        assert record.correlation_id == "existing-correlation-id"
    
    def test_filter_handles_missing_correlation_id_attribute(self):
        """Test filter when correlation_id attribute doesn't exist."""
        filter_instance = CorrelationIDFilter()
        # No _correlation_id set
        
        record = Mock()
        # Remove correlation_id attribute to simulate hasattr returning False
        if hasattr(record, 'correlation_id'):
            del record.correlation_id
        
        result = filter_instance.filter(record)
        
        assert result is True
        assert record.correlation_id == "unknown"


class TestStructuredLogger:
    """Test structured logging functionality."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test_logger")
        
        assert logger.logger.name == "test_logger"
        assert isinstance(logger.correlation_filter, CorrelationIDFilter)
    
    def test_correlation_context_manager(self):
        """Test correlation context manager."""
        logger = StructuredLogger("test_logger")
        test_correlation_id = "test-correlation-123"
        
        with logger.correlation_context(test_correlation_id) as correlation_id:
            assert correlation_id == test_correlation_id
            assert logger.correlation_filter._correlation_id == test_correlation_id
        
        # Should be cleaned up after context
        assert not hasattr(logger.correlation_filter, '_correlation_id')
    
    def test_correlation_context_generates_id_when_none_provided(self):
        """Test that correlation context generates ID when none provided."""
        logger = StructuredLogger("test_logger")
        
        with logger.correlation_context() as correlation_id:
            assert correlation_id is not None
            assert len(correlation_id) > 0
            # Should be a valid UUID format
            uuid.UUID(correlation_id)  # Will raise if invalid
    
    @patch('logging.getLogger')
    def test_structured_logging_methods(self, mock_get_logger):
        """Test structured logging methods."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        mock_logger_instance.handlers = []  # Simulate no existing handlers
        
        logger = StructuredLogger("test_logger")
        
        # Test info logging
        logger.info("Test message", key1="value1", key2="value2")
        mock_logger_instance.info.assert_called_with("Test message key1=value1 key2=value2")
        
        # Test warning logging
        logger.warning("Warning message", error="test_error")
        mock_logger_instance.warning.assert_called_with("Warning message error=test_error")
        
        # Test error logging
        logger.error("Error message", status_code=500)
        mock_logger_instance.error.assert_called_with("Error message status_code=500")
        
        # Test debug logging
        logger.debug("Debug message")
        mock_logger_instance.debug.assert_called_with("Debug message")


class TestRetryConfig:
    """Test retry configuration."""
    
    def test_default_retry_config(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_retry_config(self):
        """Test custom retry configuration values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestRetryableErrors:
    """Test retryable error classes."""
    
    def test_rate_limit_error(self):
        """Test RateLimitError creation."""
        error = RateLimitError("Rate limited", retry_after=30)
        
        assert str(error) == "Rate limited"
        assert error.retry_after == 30
        assert isinstance(error, Exception)
    
    def test_rate_limit_error_without_retry_after(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("Rate limited")
        
        assert str(error) == "Rate limited"
        assert error.retry_after is None
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError creation."""
        error = ServiceUnavailableError("Service down")
        
        assert str(error) == "Service down"
        assert isinstance(error, Exception)


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    def test_successful_function_no_retry(self):
        """Test that successful function executes without retry."""
        call_count = 0
        
        @with_retry()
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_retryable_error(self):
        """Test retry behavior on retryable errors."""
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited")
            return "success"
        
        result = failing_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Always fails")
        
        with pytest.raises(RateLimitError, match="Always fails"):
            always_failing_function()
        
        assert call_count == 3  # Initial call + 2 retries
    
    def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors don't trigger retries."""
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        def non_retryable_error_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError, match="Non-retryable error"):
            non_retryable_error_function()
        
        assert call_count == 1  # No retries
    
    def test_rate_limit_error_with_retry_after(self):
        """Test retry behavior with rate limit retry-after header."""
        call_count = 0
        start_time = time.time()
        
        @with_retry(RetryConfig(max_retries=1, base_delay=0.01, jitter=False))
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limited", retry_after=0.05)
            return "success"
        
        result = rate_limited_function()
        end_time = time.time()
        
        assert result == "success"
        assert call_count == 2
        # Should have waited at least the retry_after time
        assert (end_time - start_time) >= 0.04
    
    @patch('time.sleep')
    def test_exponential_backoff_calculation(self, mock_sleep):
        """Test exponential backoff delay calculation."""
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3, base_delay=1.0, exponential_base=2.0, jitter=False))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ServiceUnavailableError("Service down")
            return "success"
        
        result = failing_function()
        
        assert result == "success"
        assert call_count == 4
        
        # Check that sleep was called with exponential backoff delays
        expected_delays = [1.0, 2.0, 4.0]  # base_delay * (exponential_base ** attempt)
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        
        assert len(actual_delays) == 3
        for expected, actual in zip(expected_delays, actual_delays):
            assert abs(actual - expected) < 0.1  # Allow small variance


class TestErrorResponseCreation:
    """Test error response creation functionality."""
    
    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response(
            error_type="TEST_ERROR",
            detail="Test error message",
            error_code="TEST_001"
        )
        
        assert isinstance(response, ErrorResponse)
        assert response.error == "TEST_ERROR"
        assert response.detail == "Test error message"
        assert response.error_code == "TEST_001"
        assert isinstance(response.timestamp, datetime)
        assert response.request_id is not None
    
    def test_create_error_response_with_correlation_id(self):
        """Test error response creation with correlation ID."""
        correlation_id = "test-correlation-123"
        
        response = create_error_response(
            error_type="TEST_ERROR",
            detail="Test error message",
            error_code="TEST_001",
            correlation_id=correlation_id
        )
        
        assert response.request_id == correlation_id
    
    def test_create_error_response_with_logging(self):
        """Test error response creation with logging."""
        mock_logger = Mock()
        
        response = create_error_response(
            error_type="TEST_ERROR",
            detail="Test error message",
            error_code="TEST_001",
            logger=mock_logger
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Error response created: TEST_ERROR" in call_args[0][0]


class TestEnvironmentValidation:
    """Test environment variable validation."""
    
    def test_validate_environment_variables_success(self):
        """Test successful environment validation."""
        required_vars = {
            "TEST_VAR1": "Test variable 1",
            "TEST_VAR2": "Test variable 2"
        }
        
        with patch.dict(os.environ, {"TEST_VAR1": "value1", "TEST_VAR2": "value2"}):
            result = validate_environment_variables(required_vars)
            
            assert result == {"TEST_VAR1": "value1", "TEST_VAR2": "value2"}
    
    def test_validate_environment_variables_missing(self):
        """Test validation with missing environment variables."""
        required_vars = {
            "MISSING_VAR1": "Missing variable 1",
            "MISSING_VAR2": "Missing variable 2"
        }
        
        # Ensure variables are not set
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment_variables(required_vars)
            
            error_message = str(exc_info.value)
            assert "Missing environment variables" in error_message
            assert "MISSING_VAR1 (Missing variable 1)" in error_message
            assert "MISSING_VAR2 (Missing variable 2)" in error_message
    
    def test_validate_environment_variables_empty(self):
        """Test validation with empty environment variables."""
        required_vars = {
            "EMPTY_VAR1": "Empty variable 1",
            "EMPTY_VAR2": "Empty variable 2"
        }
        
        with patch.dict(os.environ, {"EMPTY_VAR1": "", "EMPTY_VAR2": "   "}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment_variables(required_vars)
            
            error_message = str(exc_info.value)
            assert "Empty environment variables" in error_message
            assert "EMPTY_VAR1 (Empty variable 1)" in error_message
            assert "EMPTY_VAR2 (Empty variable 2)" in error_message
    
    def test_validate_environment_variables_mixed_errors(self):
        """Test validation with both missing and empty variables."""
        required_vars = {
            "MISSING_VAR": "Missing variable",
            "EMPTY_VAR": "Empty variable",
            "VALID_VAR": "Valid variable"
        }
        
        with patch.dict(os.environ, {"EMPTY_VAR": "", "VALID_VAR": "valid_value"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment_variables(required_vars)
            
            error_message = str(exc_info.value)
            assert "Missing environment variables" in error_message
            assert "Empty environment variables" in error_message
            assert "MISSING_VAR (Missing variable)" in error_message
            assert "EMPTY_VAR (Empty variable)" in error_message
    
    def test_validate_environment_variables_strips_whitespace(self):
        """Test that validation strips whitespace from values."""
        required_vars = {
            "WHITESPACE_VAR": "Variable with whitespace"
        }
        
        with patch.dict(os.environ, {"WHITESPACE_VAR": "  value_with_spaces  "}):
            result = validate_environment_variables(required_vars)
            
            assert result == {"WHITESPACE_VAR": "value_with_spaces"}


class TestErrorHandler:
    """Test centralized error handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        self.error_handler = ErrorHandler(self.mock_logger)
        self.correlation_id = "test-correlation-123"
    
    def test_handle_confluence_api_error_401(self):
        """Test handling of Confluence 401 authentication error."""
        from .confluence import ConfluenceAPIError
        
        error = ConfluenceAPIError("Auth failed", status_code=401)
        response = self.error_handler.handle_confluence_api_error(error, self.correlation_id)
        
        assert response.error == "AUTHENTICATION_ERROR"
        assert response.error_code == "CONF_AUTH_FAILED"
        assert "authentication failed" in response.detail.lower()
        assert response.request_id == self.correlation_id
    
    def test_handle_confluence_api_error_403(self):
        """Test handling of Confluence 403 authorization error."""
        from .confluence import ConfluenceAPIError
        
        error = ConfluenceAPIError("Access denied", status_code=403)
        response = self.error_handler.handle_confluence_api_error(error, self.correlation_id)
        
        assert response.error == "AUTHORIZATION_ERROR"
        assert response.error_code == "CONF_ACCESS_DENIED"
        assert "access denied" in response.detail.lower()
    
    def test_handle_confluence_api_error_404(self):
        """Test handling of Confluence 404 not found error."""
        from .confluence import ConfluenceAPIError
        
        error = ConfluenceAPIError("Page not found", status_code=404)
        response = self.error_handler.handle_confluence_api_error(error, self.correlation_id)
        
        assert response.error == "RESOURCE_NOT_FOUND"
        assert response.error_code == "CONF_NOT_FOUND"
        assert "Page not found" in response.detail
    
    def test_handle_confluence_api_error_429(self):
        """Test handling of Confluence 429 rate limit error."""
        from .confluence import ConfluenceAPIError
        
        error = ConfluenceAPIError("Rate limited", status_code=429)
        response = self.error_handler.handle_confluence_api_error(error, self.correlation_id)
        
        assert response.error == "RATE_LIMIT_ERROR"
        assert response.error_code == "CONF_RATE_LIMITED"
        assert "rate limit" in response.detail.lower()
    
    def test_handle_confluence_api_error_generic(self):
        """Test handling of generic Confluence API error."""
        from .confluence import ConfluenceAPIError
        
        error = ConfluenceAPIError("Server error", status_code=500)
        response = self.error_handler.handle_confluence_api_error(error, self.correlation_id)
        
        assert response.error == "API_ERROR"
        assert response.error_code == "CONF_500"
        assert "Server error" in response.detail
    
    def test_handle_validation_error(self):
        """Test handling of validation errors."""
        error = ValueError("Invalid input")
        response = self.error_handler.handle_validation_error(error, self.correlation_id)
        
        assert response.error == "VALIDATION_ERROR"
        assert response.error_code == "VALIDATION_FAILED"
        assert response.detail == "Invalid input"
        assert response.request_id == self.correlation_id
    
    def test_handle_vector_store_connection_error(self):
        """Test handling of vector store connection errors."""
        error = Exception("Connection failed to database")
        response = self.error_handler.handle_vector_store_error(error, self.correlation_id)
        
        assert response.error == "DATABASE_CONNECTION_ERROR"
        assert response.error_code == "VECTOR_DB_CONN_FAIL"
        assert "connection failed" in response.detail.lower()
    
    def test_handle_vector_store_timeout_error(self):
        """Test handling of vector store timeout errors."""
        error = Exception("Operation timeout occurred")
        response = self.error_handler.handle_vector_store_error(error, self.correlation_id)
        
        assert response.error == "DATABASE_TIMEOUT_ERROR"
        assert response.error_code == "VECTOR_DB_TIMEOUT"
        assert "timed out" in response.detail.lower()
    
    def test_handle_vector_store_generic_error(self):
        """Test handling of generic vector store errors."""
        error = Exception("Database error occurred")
        response = self.error_handler.handle_vector_store_error(error, self.correlation_id)
        
        assert response.error == "DATABASE_ERROR"
        assert response.error_code == "VECTOR_DB_ERROR"
        assert "Database error occurred" in response.detail
    
    def test_handle_generic_error(self):
        """Test handling of generic errors."""
        error = Exception("Unexpected error")
        response = self.error_handler.handle_generic_error(error, self.correlation_id)
        
        assert response.error == "INTERNAL_ERROR"
        assert response.error_code == "INTERNAL_ERROR"
        assert "Unexpected error" in response.detail
        assert response.request_id == self.correlation_id


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple error handling features."""
    
    @patch('time.sleep')
    def test_confluence_api_with_retry_and_logging(self, mock_sleep):
        """Test Confluence API calls with retry and structured logging."""
        mock_logger = Mock()
        
        # Create a function that fails twice then succeeds
        call_count = 0
        
        @with_retry(
            RetryConfig(max_retries=3, base_delay=0.01, jitter=False),
            logger=mock_logger
        )
        def mock_confluence_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RateLimitError("API rate limited", retry_after=1)
            return {"id": "123", "title": "Test Page"}
        
        result = mock_confluence_call()
        
        assert result == {"id": "123", "title": "Test Page"}
        assert call_count == 3
        assert mock_sleep.call_count == 2
    
    def test_error_response_with_correlation_tracking(self):
        """Test error response creation with correlation ID tracking."""
        correlation_id = str(uuid.uuid4())
        mock_logger = Mock()
        
        error_handler = ErrorHandler(mock_logger)
        
        # Simulate a validation error
        error = ValueError("Invalid page ID format")
        response = error_handler.handle_validation_error(error, correlation_id)
        
        assert response.request_id == correlation_id
        assert response.error == "VALIDATION_ERROR"
        assert response.error_code == "VALIDATION_FAILED"
        assert response.detail == "Invalid page ID format"
        
        # Verify logging was called
        mock_logger.error.assert_called_once()
    
    def test_environment_validation_on_startup(self):
        """Test environment validation during application startup."""
        required_vars = {
            "CONFLUENCE_URL": "Confluence server URL",
            "CONFLUENCE_USERNAME": "Confluence username",
            "CONFLUENCE_API_TOKEN": "Confluence API token"
        }
        
        # Test successful validation
        with patch.dict(os.environ, {
            "CONFLUENCE_URL": "https://example.atlassian.net",
            "CONFLUENCE_USERNAME": "user@example.com",
            "CONFLUENCE_API_TOKEN": "token123"
        }):
            result = validate_environment_variables(required_vars)
            
            assert len(result) == 3
            assert result["CONFLUENCE_URL"] == "https://example.atlassian.net"
            assert result["CONFLUENCE_USERNAME"] == "user@example.com"
            assert result["CONFLUENCE_API_TOKEN"] == "token123"
        
        # Test validation failure
        with patch.dict(os.environ, {"CONFLUENCE_URL": "https://example.atlassian.net"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment_variables(required_vars)
            
            error_message = str(exc_info.value)
            assert "CONFLUENCE_USERNAME" in error_message
            assert "CONFLUENCE_API_TOKEN" in error_message


if __name__ == "__main__":
    pytest.main([__file__])