"""
Comprehensive error handling and logging utilities for Confluence Integration Tool.

This module provides structured error handling, retry mechanisms, and correlation ID tracking
for improved observability and debugging.
"""

import logging
import os
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union
from datetime import datetime

from .models import ErrorResponse


class CorrelationIDFilter(logging.Filter):
    """Logging filter to add correlation IDs to log records."""
    
    def filter(self, record):
        """Add correlation ID to log record if not present."""
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = getattr(self, '_correlation_id', 'unknown')
        return True


class StructuredLogger:
    """Structured logger with correlation ID support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.correlation_filter = CorrelationIDFilter()
        self.logger.addFilter(self.correlation_filter)
        
        # Configure structured logging format
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                'correlation_id=%(correlation_id)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    @contextmanager
    def correlation_context(self, correlation_id: Optional[str] = None):
        """Context manager to set correlation ID for logging."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        old_correlation_id = getattr(self.correlation_filter, '_correlation_id', None)
        self.correlation_filter._correlation_id = correlation_id
        
        try:
            yield correlation_id
        finally:
            if old_correlation_id:
                self.correlation_filter._correlation_id = old_correlation_id
            else:
                delattr(self.correlation_filter, '_correlation_id')
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        extra_data = ' '.join([f'{k}={v}' for k, v in kwargs.items()])
        full_message = f"{message} {extra_data}".strip()
        self.logger.info(full_message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        extra_data = ' '.join([f'{k}={v}' for k, v in kwargs.items()])
        full_message = f"{message} {extra_data}".strip()
        self.logger.warning(full_message)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        extra_data = ' '.join([f'{k}={v}' for k, v in kwargs.items()])
        full_message = f"{message} {extra_data}".strip()
        self.logger.error(full_message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        extra_data = ' '.join([f'{k}={v}' for k, v in kwargs.items()])
        full_message = f"{message} {extra_data}".strip()
        self.logger.debug(full_message)


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryableError(Exception):
    """Base class for errors that should trigger retry logic."""
    pass


class RateLimitError(RetryableError):
    """Error indicating rate limiting by external service."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ServiceUnavailableError(RetryableError):
    """Error indicating external service is temporarily unavailable."""
    pass


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (RetryableError,),
    logger: Optional[StructuredLogger] = None
):
    """
    Decorator to add retry logic with exponential backoff to functions.
    
    Args:
        config: Retry configuration
        retryable_exceptions: Tuple of exception types that should trigger retries
        logger: Logger instance for retry events
    """
    if config is None:
        config = RetryConfig()
    
    if logger is None:
        logger = StructuredLogger(__name__)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_retries} retries",
                            error=str(e),
                            attempt=attempt + 1
                        )
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Handle rate limiting with specific retry-after header
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = min(e.retry_after, config.max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        delay=delay,
                        max_retries=config.max_retries
                    )
                    
                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable exception, fail immediately
                    logger.error(
                        f"Function {func.__name__} failed with non-retryable error",
                        error=str(e),
                        attempt=attempt + 1
                    )
                    raise
            
            # If we get here, all retries were exhausted
            raise last_exception
        
        return wrapper
    return decorator


def create_error_response(
    error_type: str,
    detail: str,
    error_code: str,
    correlation_id: Optional[str] = None,
    logger: Optional[StructuredLogger] = None
) -> ErrorResponse:
    """
    Create a standardized error response with logging.
    
    Args:
        error_type: Category of error (e.g., "VALIDATION_ERROR", "API_ERROR")
        detail: Detailed error message
        error_code: Specific error code for programmatic handling
        correlation_id: Request correlation ID for tracking
        logger: Logger instance for error logging
    
    Returns:
        ErrorResponse model with structured error information
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    if logger:
        logger.error(
            f"Error response created: {error_type}",
            error_code=error_code,
            detail=detail,
            correlation_id=correlation_id
        )
    
    return ErrorResponse(
        error=error_type,
        detail=detail,
        error_code=error_code,
        timestamp=datetime.utcnow(),
        request_id=correlation_id
    )


def validate_environment_variables(required_vars: Dict[str, str]) -> Dict[str, str]:
    """
    Validate that required environment variables are present and non-empty.
    
    Args:
        required_vars: Dictionary mapping env var names to descriptions
    
    Returns:
        Dictionary of validated environment variable values
    
    Raises:
        ValueError: If any required environment variables are missing or empty
    """
    missing_vars = []
    empty_vars = []
    values = {}
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        
        if value is None:
            missing_vars.append(f"{var_name} ({description})")
        elif not value.strip():
            empty_vars.append(f"{var_name} ({description})")
        else:
            values[var_name] = value.strip()
    
    errors = []
    if missing_vars:
        errors.append(f"Missing environment variables: {', '.join(missing_vars)}")
    if empty_vars:
        errors.append(f"Empty environment variables: {', '.join(empty_vars)}")
    
    if errors:
        raise ValueError(f"Environment validation failed: {'; '.join(errors)}")
    
    return values


class ErrorHandler:
    """Centralized error handling for the application."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger(__name__)
    
    def handle_confluence_api_error(self, error: Exception, correlation_id: str) -> ErrorResponse:
        """Handle Confluence API specific errors."""
        from .confluence import ConfluenceAPIError
        
        if isinstance(error, ConfluenceAPIError):
            if error.status_code == 401:
                return create_error_response(
                    error_type="AUTHENTICATION_ERROR",
                    detail="Confluence authentication failed. Check credentials.",
                    error_code="CONF_AUTH_FAILED",
                    correlation_id=correlation_id,
                    logger=self.logger
                )
            elif error.status_code == 403:
                return create_error_response(
                    error_type="AUTHORIZATION_ERROR",
                    detail="Access denied to Confluence resource.",
                    error_code="CONF_ACCESS_DENIED",
                    correlation_id=correlation_id,
                    logger=self.logger
                )
            elif error.status_code == 404:
                return create_error_response(
                    error_type="RESOURCE_NOT_FOUND",
                    detail=str(error),
                    error_code="CONF_NOT_FOUND",
                    correlation_id=correlation_id,
                    logger=self.logger
                )
            elif error.status_code == 429:
                return create_error_response(
                    error_type="RATE_LIMIT_ERROR",
                    detail="Confluence API rate limit exceeded.",
                    error_code="CONF_RATE_LIMITED",
                    correlation_id=correlation_id,
                    logger=self.logger
                )
            else:
                return create_error_response(
                    error_type="API_ERROR",
                    detail=f"Confluence API error: {str(error)}",
                    error_code=f"CONF_{error.status_code}",
                    correlation_id=correlation_id,
                    logger=self.logger
                )
        
        return create_error_response(
            error_type="UNKNOWN_ERROR",
            detail=str(error),
            error_code="UNKNOWN",
            correlation_id=correlation_id,
            logger=self.logger
        )
    
    def handle_validation_error(self, error: Exception, correlation_id: str) -> ErrorResponse:
        """Handle validation errors."""
        return create_error_response(
            error_type="VALIDATION_ERROR",
            detail=str(error),
            error_code="VALIDATION_FAILED",
            correlation_id=correlation_id,
            logger=self.logger
        )
    
    def handle_vector_store_error(self, error: Exception, correlation_id: str) -> ErrorResponse:
        """Handle vector store specific errors."""
        if "connection" in str(error).lower():
            return create_error_response(
                error_type="DATABASE_CONNECTION_ERROR",
                detail="Vector database connection failed.",
                error_code="VECTOR_DB_CONN_FAIL",
                correlation_id=correlation_id,
                logger=self.logger
            )
        elif "timeout" in str(error).lower():
            return create_error_response(
                error_type="DATABASE_TIMEOUT_ERROR",
                detail="Vector database operation timed out.",
                error_code="VECTOR_DB_TIMEOUT",
                correlation_id=correlation_id,
                logger=self.logger
            )
        else:
            return create_error_response(
                error_type="DATABASE_ERROR",
                detail=f"Vector database error: {str(error)}",
                error_code="VECTOR_DB_ERROR",
                correlation_id=correlation_id,
                logger=self.logger
            )
    
    def handle_generic_error(self, error: Exception, correlation_id: str) -> ErrorResponse:
        """Handle generic errors."""
        return create_error_response(
            error_type="INTERNAL_ERROR",
            detail=f"Internal server error: {str(error)}",
            error_code="INTERNAL_ERROR",
            correlation_id=correlation_id,
            logger=self.logger
        )


# Global error handler instance
error_handler = ErrorHandler()

# Global logger instance
logger = StructuredLogger(__name__)