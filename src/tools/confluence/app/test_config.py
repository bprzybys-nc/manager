"""
Test configuration and utilities for Confluence Integration Tool tests.

This module provides configuration, fixtures, and utilities for
integration and performance testing.
"""

import os
import tempfile
import shutil
import pytest
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import Mock

from .models import RunbookContent, RunbookMetadata


class TestConfig:
    """Configuration for integration tests."""
    
    # Confluence API settings
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "https://test.atlassian.net")
    CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME", "test@example.com")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "test_token")
    
    # Test data settings
    TEST_SPACE_KEY = os.getenv("CONFLUENCE_TEST_SPACE", "TEST")
    TEST_PAGE_ID = os.getenv("CONFLUENCE_TEST_PAGE_ID", "123456")
    TEST_PAGE_TITLE = os.getenv("CONFLUENCE_TEST_PAGE_TITLE", "Test Runbook")
    
    # Performance test settings
    PERFORMANCE_TEST_ENABLED = os.getenv("PERFORMANCE_TESTS", "false").lower() == "true"
    SLOW_TEST_ENABLED = os.getenv("SLOW_TESTS", "false").lower() == "true"
    
    # Database settings
    TEST_DB_PREFIX = "confluence_test_"
    CLEANUP_TEST_DATA = os.getenv("CLEANUP_TEST_DATA", "true").lower() == "true"
    
    @classmethod
    def is_confluence_configured(cls) -> bool:
        """Check if Confluence is properly configured for testing."""
        return all([
            cls.CONFLUENCE_URL,
            cls.CONFLUENCE_USERNAME,
            cls.CONFLUENCE_API_TOKEN
        ])
    
    @classmethod
    def skip_if_no_confluence(cls):
        """Skip test if Confluence is not configured."""
        if not cls.is_confluence_configured():
            pytest.skip("Confluence not configured for integration testing")


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_runbook_metadata(
        title: str = "Test Runbook",
        author: str = "Test Author",
        space_key: str = "TEST",
        page_id: str = "test_123",
        tags: Optional[List[str]] = None
    ) -> RunbookMetadata:
        """Create test runbook metadata."""
        if tags is None:
            tags = ["test", "runbook"]
        
        return RunbookMetadata(
            title=title,
            author=author,
            last_modified=datetime.utcnow(),
            space_key=space_key,
            page_id=page_id,
            page_url=f"https://example.com/{page_id}",
            tags=tags
        )
    
    @staticmethod
    def create_runbook_content(
        metadata: Optional[RunbookMetadata] = None,
        procedures: Optional[List[str]] = None,
        troubleshooting_steps: Optional[List[str]] = None,
        prerequisites: Optional[List[str]] = None,
        raw_content: Optional[str] = None
    ) -> RunbookContent:
        """Create test runbook content."""
        if metadata is None:
            metadata = TestDataFactory.create_runbook_metadata()
        
        if procedures is None:
            procedures = [
                "Step 1: Initialize the system",
                "Step 2: Configure settings",
                "Step 3: Verify operation"
            ]
        
        if troubleshooting_steps is None:
            troubleshooting_steps = [
                "Check system logs",
                "Verify connectivity",
                "Restart services if needed"
            ]
        
        if prerequisites is None:
            prerequisites = [
                "System access",
                "Administrative privileges"
            ]
        
        if raw_content is None:
            raw_content = f"Test runbook content for {metadata.title}"
        
        return RunbookContent(
            metadata=metadata,
            procedures=procedures,
            troubleshooting_steps=troubleshooting_steps,
            prerequisites=prerequisites,
            raw_content=raw_content,
            structured_sections={
                "overview": f"Overview of {metadata.title}",
                "procedures": "Step-by-step procedures",
                "troubleshooting": "Troubleshooting guide"
            }
        )
    
    @staticmethod
    def create_bulk_runbooks(
        count: int,
        prefix: str = "Bulk Test",
        vary_content: bool = True
    ) -> List[RunbookContent]:
        """Create multiple test runbooks for bulk operations."""
        runbooks = []
        
        categories = ["Database", "Network", "Security", "Monitoring", "Deployment"]
        operations = ["Setup", "Maintenance", "Troubleshooting", "Optimization"]
        
        for i in range(count):
            category = categories[i % len(categories)]
            operation = operations[i % len(operations)]
            
            title = f"{prefix} {category} {operation} {i + 1}"
            
            metadata = TestDataFactory.create_runbook_metadata(
                title=title,
                author=f"{category} Team",
                space_key=category[:4].upper(),
                page_id=f"bulk_test_{i}",
                tags=[category.lower(), operation.lower(), "bulk_test"]
            )
            
            if vary_content:
                # Vary content size and complexity
                content_multiplier = (i % 5) + 1
                base_procedures = [
                    f"Step 1: Prepare {category} system for {operation}",
                    f"Step 2: Execute {operation} procedures",
                    f"Step 3: Verify {operation} completion"
                ]
                procedures = base_procedures * content_multiplier
                
                base_content = f"{category} {operation} runbook content. "
                raw_content = base_content * (10 * content_multiplier)
            else:
                procedures = [
                    f"Step 1: {operation} procedure for {category}",
                    f"Step 2: Verify {operation} results"
                ]
                raw_content = f"Standard {category} {operation} content"
            
            runbook = TestDataFactory.create_runbook_content(
                metadata=metadata,
                procedures=procedures,
                raw_content=raw_content
            )
            
            runbooks.append(runbook)
        
        return runbooks
    
    @staticmethod
    def create_mock_confluence_page(
        page_id: str = "mock_123",
        title: str = "Mock Runbook",
        space_key: str = "MOCK",
        content: str = None
    ) -> Dict[str, Any]:
        """Create mock Confluence page data."""
        if content is None:
            content = f"""
            <h1>{title}</h1>
            <h2>Procedures</h2>
            <ol>
                <li>First procedure step</li>
                <li>Second procedure step</li>
                <li>Third procedure step</li>
            </ol>
            <h2>Troubleshooting</h2>
            <ul>
                <li>Check system status</li>
                <li>Review error logs</li>
                <li>Contact support if needed</li>
            </ul>
            <h2>Prerequisites</h2>
            <p>System access and administrative privileges required.</p>
            """
        
        return {
            "id": page_id,
            "title": title,
            "space": {"key": space_key},
            "version": {
                "when": "2024-01-01T00:00:00Z",
                "by": {"displayName": "Mock Author"}
            },
            "body": {
                "storage": {"value": content}
            }
        }


class TestDatabaseManager:
    """Manager for test database operations."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize test database manager."""
        self.base_dir = base_dir or tempfile.gettempdir()
        self.test_dirs = []
    
    def create_test_db_dir(self, prefix: str = "confluence_test_") -> str:
        """Create temporary directory for test database."""
        test_dir = tempfile.mkdtemp(prefix=prefix, dir=self.base_dir)
        self.test_dirs.append(test_dir)
        return test_dir
    
    def cleanup_test_dirs(self):
        """Clean up all test directories."""
        for test_dir in self.test_dirs:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)
        self.test_dirs.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if TestConfig.CLEANUP_TEST_DATA:
            self.cleanup_test_dirs()


class MockConfluenceClient:
    """Mock Confluence client for testing."""
    
    def __init__(self):
        """Initialize mock client."""
        self.pages = {}
        self.search_results = []
    
    def add_mock_page(self, page_data: Dict[str, Any]):
        """Add mock page data."""
        self.pages[page_data["id"]] = page_data
    
    def set_search_results(self, results: List[Dict[str, Any]]):
        """Set mock search results."""
        self.search_results = results
    
    def get_page_by_id(self, page_id: str) -> Dict[str, Any]:
        """Mock get page by ID."""
        if page_id not in self.pages:
            from .confluence import ConfluenceAPIError
            raise ConfluenceAPIError(f"Page {page_id} not found", status_code=404)
        return self.pages[page_id]
    
    def get_page_by_title(self, space_key: str, title: str) -> Dict[str, Any]:
        """Mock get page by title."""
        for page in self.pages.values():
            if page["space"]["key"] == space_key and page["title"] == title:
                return page
        
        from .confluence import ConfluenceAPIError
        raise ConfluenceAPIError(f"Page '{title}' not found in space '{space_key}'", status_code=404)
    
    def search_pages(self, query: str, space_key: str = None, limit: int = 25) -> List[Dict[str, Any]]:
        """Mock search pages."""
        # Simple mock implementation - return configured results
        results = self.search_results[:limit]
        
        # Filter by space if specified
        if space_key:
            results = [r for r in results if r.get("space", {}).get("key") == space_key]
        
        return results
    
    def extract_runbook_content(self, page_data: Dict[str, Any]) -> RunbookContent:
        """Mock runbook content extraction."""
        metadata = TestDataFactory.create_runbook_metadata(
            title=page_data["title"],
            author=page_data["version"]["by"]["displayName"],
            space_key=page_data["space"]["key"],
            page_id=page_data["id"]
        )
        
        return TestDataFactory.create_runbook_content(metadata=metadata)


class TestMetrics:
    """Utilities for collecting test metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {}
    
    def record_time(self, operation: str, duration: float):
        """Record operation duration."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_average_time(self, operation: str) -> float:
        """Get average time for operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return sum(self.metrics[operation]) / len(self.metrics[operation])
    
    def get_max_time(self, operation: str) -> float:
        """Get maximum time for operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return max(self.metrics[operation])
    
    def get_min_time(self, operation: str) -> float:
        """Get minimum time for operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return min(self.metrics[operation])
    
    def print_summary(self):
        """Print metrics summary."""
        print("\n=== Test Metrics Summary ===")
        for operation, times in self.metrics.items():
            if times:
                avg = sum(times) / len(times)
                print(f"{operation}: avg={avg:.3f}s, max={max(times):.3f}s, "
                      f"min={min(times):.3f}s, count={len(times)}")
        print("============================\n")


# Pytest fixtures for common test utilities
@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory()


@pytest.fixture
def test_db_manager():
    """Provide test database manager with cleanup."""
    with TestDatabaseManager() as manager:
        yield manager


@pytest.fixture
def mock_confluence_client():
    """Provide mock Confluence client."""
    return MockConfluenceClient()


@pytest.fixture
def test_metrics():
    """Provide test metrics collector."""
    metrics = TestMetrics()
    yield metrics
    metrics.print_summary()


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running test"
    )
    config.addinivalue_line(
        "markers", "confluence_api: mark test as requiring real Confluence API"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on configuration."""
    # Skip performance tests if not enabled
    if not TestConfig.PERFORMANCE_TEST_ENABLED:
        skip_performance = pytest.mark.skip(reason="Performance tests disabled")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_performance)
    
    # Skip slow tests if not enabled
    if not TestConfig.SLOW_TEST_ENABLED:
        skip_slow = pytest.mark.skip(reason="Slow tests disabled")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    # Skip Confluence API tests if not configured
    if not TestConfig.is_confluence_configured():
        skip_confluence = pytest.mark.skip(reason="Confluence API not configured")
        for item in items:
            if "confluence_api" in item.keywords:
                item.add_marker(skip_confluence)