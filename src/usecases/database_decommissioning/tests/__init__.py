"""
Database Decommissioning Use Case Tests.

This package contains comprehensive tests for the database decommissioning use case
with Manager integration while preserving GraphMCP framework test patterns.

Test Structure:
- unit/: Unit tests for individual components
- integration/: Integration tests for component interactions
- conftest.py: Test fixtures and configuration
- pytest.ini: Test runner configuration

Manager Integration Tests:
- Tenant-aware functionality
- Database client integration
- Azure OpenAI integration
- FastAPI route testing
- Celery task testing

GraphMCP Compatibility Tests:
- Workflow builder patterns
- MCP client integration
- Async context management
- Error handling patterns
- Data model serialization

Test Categories (use pytest markers):
- @pytest.mark.unit: Unit tests
- @pytest.mark.integration: Integration tests
- @pytest.mark.asyncio: Async tests
- @pytest.mark.manager: Manager-specific tests
- @pytest.mark.tenant: Tenant-aware tests
- @pytest.mark.slow: Performance/slow tests

Usage:
    # Run all tests
    pytest

    # Run specific categories
    pytest -m unit
    pytest -m integration
    pytest -m "unit and manager"
    pytest -m "not slow"

    # Run specific test files
    pytest tests/unit/test_models.py
    pytest tests/integration/

    # Run with coverage
    pytest --cov=app --cov-report=html

Test Fixtures:
- workflow_config: Standard WorkflowConfig for testing
- mock_database_client: Mock Manager database client
- mock_mcp_clients: Mock MCP client instances
- test_data_generator: Generate realistic test data
- mock_discovery_result: Sample pattern discovery result
- mock_validation_results: Sample validation results
"""

# Version information for test suite
__version__ = "1.0.0"
__test_framework__ = "pytest"
__test_categories__ = [
    "unit",
    "integration",
    "asyncio",
    "manager",
    "tenant",
    "slow",
]