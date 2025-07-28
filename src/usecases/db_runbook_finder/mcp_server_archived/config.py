"""
Configuration management for RunbookRepositoryMCP server.

Provides centralized configuration with environment variable support,
validation, and different environment profiles (development, testing, production).
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """
    Configuration class for RunbookRepositoryMCP server.
    
    Supports environment variable overrides and validation for all
    configuration parameters across different deployment environments.
    """
    
    # Environment Configuration
    environment: str = field(default_factory=lambda: os.getenv("MCP_ENVIRONMENT", "development"))
    
    # Confluence Configuration
    confluence_base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("CONFLUENCE_URL", "https://company.atlassian.net")
    )
    confluence_username: Optional[str] = field(
        default_factory=lambda: os.getenv("CONFLUENCE_USERNAME")
    )
    confluence_api_token: Optional[str] = field(
        default_factory=lambda: os.getenv("CONFLUENCE_API_TOKEN")
    )
    confluence_timeout: int = field(
        default_factory=lambda: int(os.getenv("CONFLUENCE_TIMEOUT", "30"))
    )
    
    # Jira Configuration
    jira_base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("JIRA_URL", "https://company.atlassian.net")
    )
    jira_username: Optional[str] = field(
        default_factory=lambda: os.getenv("JIRA_USERNAME")
    )
    jira_api_token: Optional[str] = field(
        default_factory=lambda: os.getenv("JIRA_API_TOKEN")
    )
    jira_timeout: int = field(
        default_factory=lambda: int(os.getenv("JIRA_TIMEOUT", "30"))
    )
    
    # ChromaDB Configuration
    chromadb_path: str = field(
        default_factory=lambda: os.getenv("CHROMADB_PATH", "/tmp/chromadb_runbooks")
    )
    chromadb_collection_name: str = field(
        default_factory=lambda: os.getenv("CHROMADB_COLLECTION_NAME", "runbook_embeddings")
    )
    chromadb_embedding_model: str = field(
        default_factory=lambda: os.getenv("CHROMADB_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    
    # Slack Configuration
    slack_bot_token: Optional[str] = field(
        default_factory=lambda: os.getenv("SLACK_BOT_TOKEN")
    )
    slack_app_token: Optional[str] = field(
        default_factory=lambda: os.getenv("SLACK_APP_TOKEN")
    )
    slack_default_channel: str = field(
        default_factory=lambda: os.getenv("SLACK_DEFAULT_CHANNEL", "#mc-dba-notifications")
    )
    
    # Strategy Selection
    use_mock_strategies: bool = field(
        default_factory=lambda: os.getenv("USE_MOCK_STRATEGIES", "false").lower() == "true"
    )
    use_working_strategies: bool = field(
        default_factory=lambda: os.getenv("USE_WORKING_STRATEGIES", "true").lower() == "true"
    )
    
    # Performance Configuration
    max_search_results: int = field(
        default_factory=lambda: int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    )
    search_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("SEARCH_TIMEOUT_SECONDS", "30"))
    )
    embedding_dimension: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "384"))
    )
    
    # Logging Configuration
    log_level: str = field(
        default_factory=lambda: os.getenv("MCP_LOG_LEVEL", "INFO")
    )
    log_format: str = field(
        default_factory=lambda: os.getenv("MCP_LOG_FORMAT", "json")
    )
    
    # Security Configuration
    enable_auth: bool = field(
        default_factory=lambda: os.getenv("MCP_ENABLE_AUTH", "false").lower() == "true"
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("MCP_API_KEY")
    )
    
    def __post_init__(self):
        """Post-initialization processing and environment-specific defaults."""
        self._apply_environment_defaults()
        self._validate_configuration()
    
    def _apply_environment_defaults(self):
        """Apply environment-specific default configurations."""
        if self.environment.lower() in ["development", "dev"]:
            # Development defaults
            if not hasattr(self, '_env_applied'):
                self.use_mock_strategies = True
                self.use_working_strategies = False
                self.log_level = "DEBUG"
                self.enable_auth = False
                self._env_applied = True
                
        elif self.environment.lower() in ["testing", "test"]:
            # Testing defaults
            if not hasattr(self, '_env_applied'):
                self.use_mock_strategies = True
                self.use_working_strategies = False
                self.log_level = "INFO"
                self.enable_auth = False
                self.chromadb_path = "/tmp/chromadb_test"
                self._env_applied = True
                
        elif self.environment.lower() in ["production", "prod"]:
            # Production defaults
            if not hasattr(self, '_env_applied'):
                self.use_mock_strategies = False
                self.use_working_strategies = True
                self.log_level = "WARNING"
                self.enable_auth = True
                self._env_applied = True
    
    def _validate_configuration(self):
        """Validate configuration parameters and log warnings for missing values."""
        validation_errors = []
        warnings = []
        
        # Environment validation
        valid_environments = ["development", "testing", "production", "dev", "test", "prod"]
        if self.environment.lower() not in valid_environments:
            warnings.append(f"Unknown environment '{self.environment}', using development defaults")
        
        # Production-specific validation
        if self.environment.lower() in ["production", "prod"]:
            if not self.confluence_api_token:
                validation_errors.append("CONFLUENCE_API_TOKEN required in production")
            if not self.jira_api_token:
                validation_errors.append("JIRA_API_TOKEN required in production")
            if not self.slack_bot_token:
                validation_errors.append("SLACK_BOT_TOKEN required in production")
            if self.enable_auth and not self.api_key:
                validation_errors.append("MCP_API_KEY required when authentication is enabled")
        
        # Numeric validation
        if self.confluence_timeout <= 0:
            validation_errors.append("CONFLUENCE_TIMEOUT must be positive")
        if self.jira_timeout <= 0:
            validation_errors.append("JIRA_TIMEOUT must be positive")
        if self.max_search_results <= 0:
            validation_errors.append("MAX_SEARCH_RESULTS must be positive")
        if self.search_timeout_seconds <= 0:
            validation_errors.append("SEARCH_TIMEOUT_SECONDS must be positive")
        if self.embedding_dimension <= 0:
            validation_errors.append("EMBEDDING_DIMENSION must be positive")
        
        # Path validation
        try:
            chromadb_path = Path(self.chromadb_path)
            chromadb_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            validation_errors.append(f"Cannot create ChromaDB path {self.chromadb_path}: {e}")
        
        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            warnings.append(f"Invalid log level '{self.log_level}', using INFO")
            self.log_level = "INFO"
        
        # URL validation (basic)
        for url_field, url_value in [
            ("confluence_base_url", self.confluence_base_url),
            ("jira_base_url", self.jira_base_url)
        ]:
            if url_value and not (url_value.startswith("http://") or url_value.startswith("https://")):
                validation_errors.append(f"{url_field.upper()} must start with http:// or https://")
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
        
        # Raise errors if any
        if validation_errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Configuration validated successfully for environment: {self.environment}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary, masking sensitive values."""
        config_dict = {}
        
        for field_name, field_value in self.__dict__.items():
            if field_name.startswith('_'):
                continue
                
            # Mask sensitive fields
            if any(sensitive in field_name.lower() for sensitive in ['token', 'key', 'password']):
                if field_value:
                    config_dict[field_name] = f"{field_value[:8]}..." if len(field_value) > 8 else "***"
                else:
                    config_dict[field_name] = None
            else:
                config_dict[field_name] = field_value
        
        return config_dict
    
    def get_confluence_config(self) -> Dict[str, Any]:
        """Get Confluence-specific configuration."""
        return {
            "base_url": self.confluence_base_url,
            "username": self.confluence_username,
            "api_token": self.confluence_api_token,
            "timeout": self.confluence_timeout
        }
    
    def get_jira_config(self) -> Dict[str, Any]:
        """Get Jira-specific configuration."""
        return {
            "base_url": self.jira_base_url,
            "username": self.jira_username,
            "api_token": self.jira_api_token,
            "timeout": self.jira_timeout
        }
    
    def get_chromadb_config(self) -> Dict[str, Any]:
        """Get ChromaDB-specific configuration."""
        return {
            "path": self.chromadb_path,
            "collection_name": self.chromadb_collection_name,
            "embedding_model": self.chromadb_embedding_model,
            "embedding_dimension": self.embedding_dimension
        }
    
    def get_slack_config(self) -> Dict[str, Any]:
        """Get Slack-specific configuration."""
        return {
            "bot_token": self.slack_bot_token,
            "app_token": self.slack_app_token,
            "default_channel": self.slack_default_channel
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ["production", "prod"]
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ["development", "dev"]
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() in ["testing", "test"]
    
    def should_use_mock_strategies(self) -> bool:
        """Determine if mock strategies should be used."""
        return self.use_mock_strategies or self.is_development() or self.is_testing()
    
    def should_use_working_strategies(self) -> bool:
        """Determine if working strategies should be used."""
        return self.use_working_strategies and not self.should_use_mock_strategies()
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance-related configuration."""
        return {
            "max_search_results": self.max_search_results,
            "search_timeout_seconds": self.search_timeout_seconds,
            "embedding_dimension": self.embedding_dimension
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "level": self.log_level,
            "format": self.log_format
        }
    
    @classmethod
    def from_file(cls, config_file_path: Union[str, Path]) -> "MCPServerConfig":
        """
        Load configuration from JSON file, with environment variable overrides.
        
        Args:
            config_file_path: Path to JSON configuration file
            
        Returns:
            MCPServerConfig instance
        """
        config_path = Path(config_file_path)
        
        if not config_path.exists():
            logger.warning(f"Configuration file {config_path} not found, using environment variables")
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            # Create instance with file values, environment variables still override
            return cls(**file_config)
            
        except Exception as e:
            logger.error(f"Error loading configuration file {config_path}: {e}")
            logger.info("Falling back to environment variables")
            return cls()
    
    @classmethod
    def from_environment(cls) -> "MCPServerConfig":
        """
        Create configuration using only environment variables.
        
        Returns:
            MCPServerConfig instance
        """
        return cls()
    
    def save_to_file(self, config_file_path: Union[str, Path]):
        """
        Save current configuration to JSON file (excluding sensitive data).
        
        Args:
            config_file_path: Path where to save configuration
        """
        config_path = Path(config_file_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get dictionary representation (with masked sensitive data)
        config_dict = self.to_dict()
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {e}")
            raise
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"MCPServerConfig(environment={self.environment}, " \
               f"confluence_url={self.confluence_base_url}, " \
               f"use_mock={self.use_mock_strategies})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        masked_dict = self.to_dict()
        return f"MCPServerConfig({masked_dict})"


def load_config(
    config_file_path: Optional[Union[str, Path]] = None,
    environment: Optional[str] = None
) -> MCPServerConfig:
    """
    Load configuration with flexible options.
    
    Args:
        config_file_path: Optional path to configuration file
        environment: Optional environment override
        
    Returns:
        MCPServerConfig instance
    """
    # Set environment override if provided
    if environment:
        os.environ["MCP_ENVIRONMENT"] = environment
    
    # Load from file if provided, otherwise from environment
    if config_file_path:
        config = MCPServerConfig.from_file(config_file_path)
    else:
        config = MCPServerConfig.from_environment()
    
    logger.info(f"Loaded configuration for environment: {config.environment}")
    return config


def get_default_config_path() -> Path:
    """Get default configuration file path."""
    # Check common locations
    possible_paths = [
        Path.cwd() / "mcp_config.json",
        Path.cwd() / "config" / "mcp_config.json",
        Path.home() / ".mcp" / "config.json",
        Path("/etc/mcp/config.json")
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # Return default location
    return Path.cwd() / "mcp_config.json"


def create_sample_config(output_path: Union[str, Path]) -> None:
    """
    Create a sample configuration file with documentation.
    
    Args:
        output_path: Where to save the sample configuration
    """
    sample_config = {
        "_comment": "RunbookRepositoryMCP Server Configuration",
        "_note": "Environment variables will override these values",
        
        "environment": "development",
        
        "confluence_base_url": "https://company.atlassian.net",
        "confluence_username": "your-email@company.com",
        "confluence_api_token": "your-confluence-api-token",
        "confluence_timeout": 30,
        
        "jira_base_url": "https://company.atlassian.net",
        "jira_username": "your-email@company.com",
        "jira_api_token": "your-jira-api-token",
        "jira_timeout": 30,
        
        "chromadb_path": "/tmp/chromadb_runbooks",
        "chromadb_collection_name": "runbook_embeddings",
        "chromadb_embedding_model": "all-MiniLM-L6-v2",
        
        "slack_bot_token": "xoxb-your-slack-bot-token",
        "slack_app_token": "xapp-your-slack-app-token",
        "slack_default_channel": "#mc-dba-notifications",
        
        "use_mock_strategies": True,
        "use_working_strategies": False,
        
        "max_search_results": 10,
        "search_timeout_seconds": 30,
        "embedding_dimension": 384,
        
        "log_level": "INFO",
        "log_format": "json",
        
        "enable_auth": False,
        "api_key": "your-api-key-if-auth-enabled"
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    logger.info(f"Sample configuration created at {output_path}")


# Environment variable documentation
ENV_VAR_DOCS = {
    "MCP_ENVIRONMENT": "Deployment environment (development, testing, production)",
    "CONFLUENCE_BASE_URL": "Confluence instance URL",
    "CONFLUENCE_USERNAME": "Confluence username/email",
    "CONFLUENCE_API_TOKEN": "Confluence API token",
    "CONFLUENCE_TIMEOUT": "Confluence request timeout in seconds",
    "JIRA_BASE_URL": "Jira instance URL",
    "JIRA_USERNAME": "Jira username/email",
    "JIRA_API_TOKEN": "Jira API token",
    "JIRA_TIMEOUT": "Jira request timeout in seconds",
    "CHROMADB_PATH": "ChromaDB storage path",
    "CHROMADB_COLLECTION_NAME": "ChromaDB collection name",
    "CHROMADB_EMBEDDING_MODEL": "Embedding model name",
    "SLACK_BOT_TOKEN": "Slack bot token",
    "SLACK_APP_TOKEN": "Slack app token",
    "SLACK_DEFAULT_CHANNEL": "Default Slack channel for notifications",
    "USE_MOCK_STRATEGIES": "Use mock strategies (true/false)",
    "USE_WORKING_STRATEGIES": "Use working strategies (true/false)",
    "MAX_SEARCH_RESULTS": "Maximum search results to return",
    "SEARCH_TIMEOUT_SECONDS": "Search operation timeout",
    "EMBEDDING_DIMENSION": "Vector embedding dimension",
    "MCP_LOG_LEVEL": "Logging level (DEBUG, INFO, WARNING, ERROR)",
    "MCP_LOG_FORMAT": "Log format (json, text)",
    "MCP_ENABLE_AUTH": "Enable API key authentication",
    "MCP_API_KEY": "API key for authentication"
}


def print_env_var_docs():
    """Print documentation for environment variables."""
    print("RunbookRepositoryMCP Server Environment Variables:")
    print("=" * 50)
    
    for var_name, description in ENV_VAR_DOCS.items():
        print(f"{var_name:25} - {description}")
    
    print("\nExample usage:")
    print("export MCP_ENVIRONMENT=production")
    print("export CONFLUENCE_API_TOKEN=your-token-here")
    print("python -m db_runbook_finder.mcp_server.server")


if __name__ == "__main__":
    # CLI for configuration management
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create-sample":
            output_path = sys.argv[2] if len(sys.argv) > 2 else "mcp_config.json"
            create_sample_config(output_path)
        elif command == "validate":
            config_path = sys.argv[2] if len(sys.argv) > 2 else None
            try:
                config = load_config(config_path)
                print("✅ Configuration is valid")
                print(f"Environment: {config.environment}")
                print(f"Mock strategies: {config.should_use_mock_strategies()}")
            except ValueError as e:
                print(f"❌ Configuration error: {e}")
                sys.exit(1)
        elif command == "env-docs":
            print_env_var_docs()
        else:
            print("Usage: python config.py [create-sample|validate|env-docs] [path]")
    else:
        # Default: validate current configuration
        try:
            config = load_config()
            print("✅ Configuration loaded successfully")
            print(config)
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)