"""
Test configuration for database decommissioning use case tests.

This module provides test fixtures and configuration for the database decommissioning
use case with Manager integration while preserving GraphMCP framework test patterns.
"""

import sys
import pytest
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock

# Add Manager project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add database_decommissioning directory to path for local imports
local_root = Path(__file__).parent.parent
sys.path.insert(0, str(local_root))

# Manager imports for fixtures
import src.config as config
from src.database.client import DatabaseClient

# Local imports
from app.models import WorkflowConfig, WorkflowExecutionResult
from app.utils import create_logger_for_workflow


# Core fixtures from GraphMCP pattern
@pytest.fixture
def mock_config_path():
    """Provide a mock config path for testing."""
    return "test_config.json"


@pytest.fixture
def postgres_air_database():
    """Provide test database name."""
    return "postgres_air"


@pytest.fixture
def test_tenant_id():
    """Provide test tenant ID for Manager integration."""
    return "test_tenant_123"


@pytest.fixture
def test_workflow_id():
    """Provide test workflow ID."""
    return "test_workflow_123"


# Manager-specific fixtures
@pytest.fixture
def mock_manager_config():
    """Mock Manager configuration."""
    mock_config = Mock()
    mock_config.MONGO_DB_URI = "mongodb://localhost:27017/test_db"
    mock_config.AZURE_OPENAI_API_KEY = "test_api_key"
    mock_config.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
    mock_config.PROMETHEUS_ADDRESS = "http://localhost:9090"
    mock_config.MANAGER_API_ADDRESS = "localhost:9123"
    return mock_config


@pytest.fixture
def mock_database_client():
    """Mock Manager database client."""
    client = Mock(spec=DatabaseClient)
    client.database = {}
    
    # Mock collections
    collections = {
        "validation_results": Mock(),
        "risk_assessments": Mock(),
        "workflow_executions": Mock(),
    }
    
    for name, collection in collections.items():
        collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
        collection.find_one = AsyncMock(return_value=None)
        collection.find = AsyncMock(return_value=[])
        client.database[name] = collection
    
    return client


@pytest.fixture
def workflow_config(postgres_air_database, test_tenant_id):
    """Create test workflow configuration."""
    return WorkflowConfig(
        database_name=postgres_air_database,
        repo_owner="test_owner",
        repo_name="test_repo",
        tenant_id=test_tenant_id,
        user_id="test_user",
        max_parallel_steps=2,
        default_timeout=30,
        debug_mode=True,
    )


@pytest.fixture
def mock_discovery_result():
    """Mock pattern discovery result."""
    return {
        "files": [
            {
                "path": "app/models.py",
                "content": "from postgres_air import connection",
                "source_type": "python",
                "confidence": "high",
            },
            {
                "path": "config/database.yml",
                "content": "database: postgres_air",
                "source_type": "config",
                "confidence": "medium",
            },
            {
                "path": "sql/create_tables.sql",
                "content": "CREATE DATABASE postgres_air;",
                "source_type": "sql",
                "confidence": "high",
            },
        ],
        "files_by_type": {
            "python": [
                {
                    "path": "app/models.py",
                    "content": "from postgres_air import connection",
                    "source_type": "python",
                    "confidence": "high",
                }
            ],
            "config": [
                {
                    "path": "config/database.yml",
                    "content": "database: postgres_air",
                    "source_type": "config",
                    "confidence": "medium",
                }
            ],
            "sql": [
                {
                    "path": "sql/create_tables.sql",
                    "content": "CREATE DATABASE postgres_air;",
                    "source_type": "sql",
                    "confidence": "high",
                }
            ],
        },
        "confidence_distribution": {"high": 2, "medium": 1, "low": 0},
        "repository_stats": {"total_files": 10, "analyzed_files": 3},
    }


@pytest.fixture
def mock_validation_results():
    """Mock validation results."""
    return [
        {
            "rule_type": "database_reference",
            "status": "passed",
            "confidence": 95,
            "description": "No direct references found",
            "details": {
                "total_files": 3,
                "references_found": 0,
                "file_analysis": [],
            },
        },
        {
            "rule_type": "rule_compliance",
            "status": "passed",
            "confidence": 85,
            "description": "Good pattern discovery quality",
            "details": {
                "total_files": 3,
                "pattern_quality": {"high_confidence": 2, "medium_confidence": 1, "low_confidence": 0},
            },
        },
        {
            "rule_type": "service_integrity",
            "status": "warning",
            "confidence": 70,
            "description": "Medium impact detected",
            "details": {
                "total_files": 3,
                "critical_files": 2,
                "risk_assessment": {"level": "MEDIUM"},
            },
        },
    ]


@pytest.fixture
def mock_mcp_clients():
    """Mock MCP client instances."""
    github_client = Mock()
    github_client.SERVER_NAME = "ovr_github"
    github_client.__aenter__ = AsyncMock(return_value=github_client)
    github_client.__aexit__ = AsyncMock(return_value=None)
    github_client.analyze_repository = AsyncMock(
        return_value={"status": "success", "analysis": "test_analysis"}
    )
    github_client.create_pull_request = AsyncMock(
        return_value={"status": "success", "pr_url": "https://github.com/test/pr/1"}
    )

    slack_client = Mock()
    slack_client.SERVER_NAME = "ovr_slack"
    slack_client.__aenter__ = AsyncMock(return_value=slack_client)
    slack_client.__aexit__ = AsyncMock(return_value=None)
    slack_client.post_notification = AsyncMock(
        return_value={"status": "success", "message_id": "test_message_id"}
    )

    repomix_client = Mock()
    repomix_client.SERVER_NAME = "ovr_repomix"
    repomix_client.__aenter__ = AsyncMock(return_value=repomix_client)
    repomix_client.__aexit__ = AsyncMock(return_value=None)
    repomix_client.pack_repository = AsyncMock(
        return_value={"status": "success", "output_id": "test_output_id"}
    )
    repomix_client.search_content = AsyncMock(
        return_value={"status": "success", "matches": []}
    )

    return {
        "github": github_client,
        "slack": slack_client,
        "repomix": repomix_client,
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.log_info = Mock()
    logger.log_error = Mock()
    logger.log_warning = Mock()
    logger.log_workflow_start = Mock()
    logger.log_workflow_end = Mock()
    logger.log_step_start = Mock()
    logger.log_step_end = Mock()
    logger.log_table = Mock()
    return logger


@pytest.fixture
async def mock_step_function():
    """Mock step function for workflow testing."""
    async def step_function(context, step, **params):
        return {
            "status": "completed",
            "test_param": params.get("test_param", "default"),
            "execution_time": 0.001,
        }
    return step_function


@pytest.fixture
def mock_azure_openai_client():
    """Mock Azure OpenAI client."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"analysis": "test", "confidence": "high", "recommendations": []}'
                    )
                )
            ]
        )
    )
    return client


@pytest.fixture
def sample_workflow_execution_result():
    """Sample workflow execution result for testing."""
    return WorkflowExecutionResult(
        workflow_id="test_workflow_123",
        database_name="postgres_air",
        success=True,
        duration_seconds=10.5,
        steps_completed=5,
        total_steps=5,
        discovery_result={"files": [], "files_by_type": {}},
        validation_results=[],
        qa_result=None,
        final_recommendations=["Test completed successfully"],
        execution_context={
            "tenant_id": "test_tenant_123",
            "user_id": "test_user",
            "timestamp": "2024-01-01T00:00:00Z",
        },
    )


# Test data generators
@pytest.fixture
def test_data_generator():
    """Test data generator for complex test scenarios."""
    class TestDataGenerator:
        def generate_file_content(self, file_type: str, database_name: str, reference_count: int = 1) -> str:
            """Generate file content with specified database references."""
            if file_type == "python":
                return f"""
import os
from {database_name} import connection

def get_data():
    return connection.query("SELECT * FROM {database_name}.users")

# Reference count: {reference_count}
"""
            elif file_type == "sql":
                return f"""
-- Database: {database_name}
CREATE DATABASE {database_name};
USE {database_name};

CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(255)
);
"""
            elif file_type == "config":
                return f"""
database:
  name: {database_name}
  host: localhost
  port: 5432
  
app:
  database_name: {database_name}
"""
            else:
                return f"# File with {reference_count} references to {database_name}"

        def generate_discovery_result(
            self, 
            database_name: str, 
            file_count: int = 5, 
            reference_density: float = 0.5
        ) -> Dict[str, Any]:
            """Generate discovery result with specified parameters."""
            files = []
            files_by_type = {"python": [], "sql": [], "config": [], "documentation": []}
            
            file_types = list(files_by_type.keys())
            references_count = int(file_count * reference_density)
            
            for i in range(file_count):
                file_type = file_types[i % len(file_types)]
                has_reference = i < references_count
                
                file_info = {
                    "path": f"test_{file_type}_{i}.{file_type}",
                    "content": self.generate_file_content(
                        file_type, database_name, 1 if has_reference else 0
                    ),
                    "source_type": file_type,
                    "confidence": "high" if has_reference else "medium",
                }
                
                files.append(file_info)
                files_by_type[file_type].append(file_info)
            
            # Calculate confidence distribution
            high_confidence = sum(1 for f in files if f["confidence"] == "high")
            medium_confidence = sum(1 for f in files if f["confidence"] == "medium")
            low_confidence = len(files) - high_confidence - medium_confidence
            
            return {
                "files": files,
                "files_by_type": files_by_type,
                "confidence_distribution": {
                    "high": high_confidence,
                    "medium": medium_confidence,
                    "low": low_confidence,
                },
                "repository_stats": {"total_files": file_count * 2, "analyzed_files": file_count},
            }

    return TestDataGenerator()


# Async testing configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()