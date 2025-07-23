"""
Test configuration and fixtures for DB Runbook Finder tests.

This module provides shared test fixtures and configuration for
the DB Runbook Finder test suite.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from src.usecases.db_runbook_finder.state import WorkflowState
from src.usecases.db_runbook_finder.nodes import DBRunbookFinderNodes
from src.usecases.db_runbook_finder.workflow import DBRunbookFinderWorkflow


@pytest.fixture
def sample_jira_key():
    """Sample Jira ticket key for testing."""
    return "AGENT-6"


@pytest.fixture
def sample_workflow_state(sample_jira_key):
    """Sample WorkflowState for testing."""
    return WorkflowState(jira_key=sample_jira_key)


@pytest.fixture
def populated_workflow_state(sample_jira_key):
    """WorkflowState with sample incident data for testing."""
    state = WorkflowState(jira_key=sample_jira_key)
    state.incident_data = {
        "summary": "Database connection timeout in production environment",
        "description": "Users experiencing intermittent database timeouts when accessing customer data.",
        "client": "Agent System",
        "project_key": "AGENT",
        "issue_type": "Incident",
        "priority": "High",
        "assignee": "John Smith",
        "status": "Open"
    }
    return state


@pytest.fixture
def workflow_state_with_runbooks(populated_workflow_state):
    """WorkflowState with sample runbook results."""
    populated_workflow_state.runbooks = [
        {
            "title": "Database Connection Troubleshooting Guide",
            "url": "https://confluence.example.com/display/MCDBA/DB+Connection+Troubleshooting",
            "space_key": "MCDBA",
            "relevance_score": 0.92,
            "excerpt": "Step-by-step guide to diagnose and resolve database connection issues..."
        },
        {
            "title": "Connection Pool Management Best Practices",
            "url": "https://confluence.example.com/display/AAVA/Connection+Pool+Management",
            "space_key": "AAVA",
            "relevance_score": 0.87,
            "excerpt": "Guidelines for configuring and monitoring database connection pools..."
        }
    ]
    return populated_workflow_state


@pytest.fixture
def workflow_state_no_runbooks(populated_workflow_state):
    """WorkflowState with no runbook results (gap scenario)."""
    populated_workflow_state.runbooks = []
    return populated_workflow_state


@pytest.fixture
def mock_jira_response():
    """Mock Jira API response for testing."""
    return {
        "fields": {
            "summary": "Database connection timeout in production environment",
            "description": "Users experiencing intermittent database timeouts when accessing customer data. Connection pool seems to be exhausted during peak hours.",
            "project": {"key": "AGENT"},
            "issuetype": {"name": "Incident"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "John Smith"},
            "status": {"name": "Open"},
            "created": "2024-07-20T10:00:00.000Z",
            "labels": ["database", "performance", "production"]
        }
    }


@pytest.fixture
def mock_confluence_response():
    """Mock Confluence search response for testing."""
    return {
        "results": [
            {
                "title": "Database Connection Troubleshooting Guide",
                "url": "https://confluence.example.com/display/MCDBA/DB+Connection+Troubleshooting",
                "space_key": "MCDBA",
                "relevance_score": 0.92,
                "excerpt": "Step-by-step guide to diagnose and resolve database connection issues..."
            },
            {
                "title": "Connection Pool Management Best Practices",
                "url": "https://confluence.example.com/display/AAVA/Connection+Pool+Management",
                "space_key": "AAVA",
                "relevance_score": 0.87,
                "excerpt": "Guidelines for configuring and monitoring database connection pools..."
            }
        ]
    }


@pytest.fixture
def mock_confluence_empty_response():
    """Mock empty Confluence search response for gap testing."""
    return {"results": []}


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock()
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def db_runbook_finder_nodes():
    """DB Runbook Finder nodes instance for testing."""
    return DBRunbookFinderNodes()


@pytest.fixture
def db_runbook_finder_workflow():
    """DB Runbook Finder workflow instance for testing."""
    return DBRunbookFinderWorkflow()


@pytest.fixture
def project_client_mappings():
    """Sample project to client mappings for testing."""
    return {
        "AGENT": "Agent System",
        "NESMCI": "Neste",
        "HEMCI": "Helvetia",
        "OVRMCI": "Ovora Internal",
        "OVR": "Ovora",
        "TEST": "Test Environment"
    }


@pytest.fixture
def mock_logging_config():
    """Mock logging configuration for testing."""
    config = Mock()
    config.from_env = Mock(return_value=config)
    config.validate = Mock()
    return config


@pytest.fixture
def performance_metrics():
    """Sample performance metrics for testing."""
    return {
        "fetch_incident": 2.5,
        "search_runbooks": 1.8,
        "update_jira_results": 1.2,
        "notify_team": 0.8
    }


@pytest.fixture
def error_scenarios():
    """Test scenarios for error handling."""
    return {
        "jira_api_error": {
            "error": "Jira API authentication failed",
            "status_code": 401
        },
        "confluence_api_error": {
            "error": "Confluence API rate limit exceeded",
            "status_code": 429
        },
        "network_timeout": {
            "error": "Network timeout occurred",
            "status_code": 504
        },
        "invalid_ticket": {
            "error": "Ticket not found",
            "status_code": 404
        }
    }


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slower, external deps)"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "error_handling: marks tests for error handling scenarios"
    )


# Custom assertion helpers
class WorkflowAssertions:
    """Custom assertions for workflow testing."""
    
    @staticmethod
    def assert_state_valid(state: WorkflowState):
        """Assert that workflow state is valid."""
        assert state is not None
        assert hasattr(state, 'jira_key')
        assert hasattr(state, 'status')
        assert hasattr(state, 'incident_data')
        assert hasattr(state, 'runbooks')
    
    @staticmethod
    def assert_state_completed(state: WorkflowState):
        """Assert that workflow state indicates completion."""
        assert state.is_completed()
        assert state.status in ["SUCCESS", "GAP_DETECTED"]
    
    @staticmethod
    def assert_state_has_runbooks(state: WorkflowState):
        """Assert that workflow state contains runbook results."""
        assert state.has_runbooks()
        assert len(state.runbooks) > 0
    
    @staticmethod
    def assert_state_no_runbooks(state: WorkflowState):
        """Assert that workflow state has no runbook results."""
        assert not state.has_runbooks()
        assert len(state.runbooks) == 0
    
    @staticmethod
    def assert_performance_within_limits(state: WorkflowState, max_duration: float = 30.0):
        """Assert that workflow performance is within acceptable limits."""
        total_duration = state.get_total_duration()
        assert total_duration <= max_duration, f"Workflow took {total_duration}s, expected <={max_duration}s"


@pytest.fixture
def workflow_assertions():
    """Provide workflow assertion helpers."""
    return WorkflowAssertions


# Mock client fixtures for external tool testing
@pytest.fixture
def client():
    """Mock FastAPI test client for external tool endpoints."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    # Create a mock FastAPI app for testing
    app = FastAPI()
    
    # Add basic mock endpoints that the tests expect
    @app.get("/runbooks")
    def list_runbooks(limit: int = 10, offset: int = 0):
        return {"runbooks": [], "pagination": {"total_count": 0}}
    
    @app.get("/search/runbooks")
    def search_runbooks(query: str = "", limit: int = 5):
        from fastapi import HTTPException
        
        # Validate parameters like real endpoint would
        if not query or query.strip() == "":
            raise HTTPException(status_code=422, detail="Query parameter cannot be empty")
        if limit <= 0:
            raise HTTPException(status_code=422, detail="Limit must be greater than 0")
        if limit > 20:
            raise HTTPException(status_code=422, detail="Limit cannot exceed 20")
            
        return {"results": [], "processing_time": 0.01}
    
    @app.get("/runbooks/{runbook_id}")
    def get_runbook(runbook_id: str):
        from fastapi import HTTPException
        
        # Validate runbook_id
        if not runbook_id or runbook_id.strip() == "":
            raise HTTPException(status_code=422, detail="Runbook ID cannot be empty")
        if runbook_id.strip() != runbook_id or runbook_id == "%20":
            raise HTTPException(status_code=422, detail="Invalid runbook ID format")
        
        # Mock not found response for most IDs
        raise HTTPException(status_code=404, detail="Runbook not found")
    
    @app.post("/pages/extract")
    def extract_page():
        return {"metadata": {"title": "Mock Runbook"}, "procedures": []}
    
    @app.post("/pages/bulk-extract")
    def bulk_extract(request_data: dict = None):
        import uuid
        job_id = f"mock-job-{uuid.uuid4().hex[:8]}"
        page_ids = request_data.get("page_ids", []) if request_data else []
        return {
            "job_id": job_id, 
            "status": "pending", 
            "total_pages": len(page_ids)
        }
    
    @app.get("/jobs/{job_id}")
    def get_job_status(job_id: str):
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:01:00Z",
            "results": {"processed": 3, "errors": 0}
        }
    
    @app.get("/jobs/statistics")
    def get_job_statistics():
        return {
            "total_jobs": 10,
            "completed_jobs": 8,
            "failed_jobs": 1,
            "pending_jobs": 1,
            "average_processing_time": 45.2
        }
    
    @app.get("/jobs")
    def list_jobs():
        return {"jobs": []}
    
    @app.get("/health")
    def health_check():
        return {
            "status": "healthy", 
            "timestamp": "2024-01-01T00:00:00Z",
            "vector_db_connected": True,
            "confluence_connected": False,
            "total_runbooks": 5
        }
    
    @app.get("/health/ready")
    def readiness_check():
        return {"status": "ready", "timestamp": "2024-01-01T00:00:00Z"}
    
    @app.get("/health/live")
    def liveness_check():
        return {"status": "alive", "timestamp": "2024-01-01T00:00:00Z"}
    
    @app.get("/metrics")
    def metrics():
        return {"runbooks_indexed": 0, "vector_dimensions": 384, "total_queries": 0}
    
    return TestClient(app)


@pytest.fixture
def data_loader():
    """Mock data loader for testing."""
    from src.usecases.db_runbook_finder.tests.data.test_data_loader import MockRunbookDataLoader
    return MockRunbookDataLoader()