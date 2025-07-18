"""Configuration settings for the Confluence tool."""

import os
from typing import Optional


class ConfluenceConfig:
    """Configuration class for Confluence API settings."""
    
    def __init__(self):
        self.url: str = os.getenv("CONFLUENCE_URL", "")
        self.username: str = os.getenv("CONFLUENCE_USERNAME", "")
        self.api_token: str = os.getenv("CONFLUENCE_API_TOKEN", "")
        self.timeout: int = int(os.getenv("CONFLUENCE_TIMEOUT", "30"))
        
    def is_configured(self) -> bool:
        """Check if all required configuration is present."""
        return bool(self.url and self.username and self.api_token)
    
    def get_auth(self) -> tuple[str, str]:
        """Get authentication tuple for API requests."""
        return (self.username, self.api_token)


# Global configuration instance
config = ConfluenceConfig()