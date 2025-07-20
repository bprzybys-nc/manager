# Database Decommissioning Use Case

A comprehensive database decommissioning workflow implementation for the Manager component, enhanced with Manager integration while preserving GraphMCP framework compatibility.

## Overview

This use case provides AI-powered database decommissioning automation with comprehensive pattern discovery, validation, quality assurance, and risk assessment capabilities. It integrates seamlessly with Manager's architecture while maintaining compatibility with the GraphMCP framework patterns.

## Features

### Core Capabilities
- **AI-Powered Pattern Discovery**: Intelligent detection of database references across codebases
- **Comprehensive Validation**: Multi-layered validation rules for database references, compliance, and service integrity
- **Quality Assurance Gates**: Automated quality validation with configurable thresholds
- **Risk Assessment**: Multi-factor risk analysis with tenant-specific considerations
- **Repository Processing**: Automated code changes and pull request creation
- **Slack Integration**: Real-time notifications and workflow progress tracking

### Manager Integration
- **Tenant-Aware Operations**: Full multi-tenant support with tenant-specific configurations
- **Database Persistence**: Workflow state and results stored in Manager's MongoDB
- **Azure OpenAI Integration**: Leverages Manager's AI configuration and clients
- **FastAPI Routes**: RESTful API endpoints following Manager patterns
- **Celery Integration**: Asynchronous workflow execution with task management
- **Prometheus Metrics**: Performance monitoring and observability

### GraphMCP Compatibility
- **Workflow Orchestration**: Full GraphMCP WorkflowBuilder integration
- **MCP Client Support**: GitHub, Slack, and Repomix client wrappers
- **Async Context Management**: Proper resource management and error handling
- **Data Model Compatibility**: Dual dataclass/Pydantic model support

## Architecture

```
database_decommissioning/
├── app/                          # Main application code
│   ├── models.py                # Data models (dataclass + Pydantic)
│   ├── utils.py                 # Utility functions and Manager integration
│   ├── orchestrator.py          # Main workflow orchestrator
│   │
│   ├── validation/              # Environment and workflow validation
│   │   ├── environment_validation.py
│   │   ├── workflow_validation.py
│   │   └── quality_assurance.py
│   │
│   ├── processors/              # Core processing engines
│   │   ├── pattern_discovery.py
│   │   ├── file_processor.py
│   │   └── repository_processor.py
│   │
│   ├── clients/                 # MCP client wrappers
│   │   ├── base.py
│   │   ├── github_client.py
│   │   ├── slack_client.py
│   │   └── repomix_client.py
│   │
│   ├── business_rules/          # Business validation and rules
│   │   ├── validation_rules.py
│   │   ├── quality_rules.py
│   │   └── risk_assessment.py
│   │
│   └── api/                     # FastAPI routes and endpoints
│       ├── routes.py
│       └── main.py
│
├── tests/                       # Comprehensive test suite
│   ├── conftest.py             # Test fixtures and configuration
│   ├── pytest.ini             # Test runner configuration
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
│
├── pyproject.toml              # Project configuration and dependencies
└── README.md                   # This file
```

## Installation

### Prerequisites
- Python 3.12 or higher
- Manager project dependencies
- MongoDB (for data persistence)
- Redis (for Celery task queue)
- Azure OpenAI account (for AI features)

### Setup

1. **Install Dependencies**:
   ```bash
   cd manager/src/usecases/database_decommissioning
   uv sync
   ```

2. **Environment Configuration**:
   ```bash
   # Required Manager environment variables
   export AZURE_OPENAI_API_KEY="your_azure_openai_key"
   export AZURE_OPENAI_ENDPOINT="your_azure_openai_endpoint"
   export MONGO_DB_URI="mongodb://localhost:27017/manager_db"
   export PROMETHEUS_ADDRESS="http://localhost:9090"
   
   # Optional for full functionality
   export SLACK_BOT_TOKEN="your_slack_bot_token"
   export GITHUB_TOKEN="your_github_token"
   ```

3. **GraphMCP Configuration**:
   Configure MCP servers in your GraphMCP configuration file:
   ```json
   {
     "mcpServers": {
       "ovr_github": {
         "command": "npx",
         "args": ["@modelcontextprotocol/server-github"],
         "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_TOKEN"}
       },
       "ovr_slack": {
         "command": "npx", 
         "args": ["@modelcontextprotocol/server-slack"],
         "env": {"SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN"}
       },
       "ovr_repomix": {
         "command": "npx",
         "args": ["@modelcontextprotocol/server-repomix"]
       }
     }
   }
   ```

## Usage

### FastAPI Routes

Start the FastAPI server:
```bash
cd manager/src/usecases/database_decommissioning
uv run uvicorn app.main:app --port 8080 --reload
```

### API Endpoints

#### Synchronous Decommissioning
```bash
POST /sync/decommission
{
  "database_name": "postgres_air",
  "repo_owner": "example_org",
  "repo_name": "example_repo",
  "tenant_id": "tenant_123",
  "user_id": "user_456"
}
```

#### Asynchronous Decommissioning
```bash
POST /async/decommission
{
  "database_name": "postgres_air",
  "repo_owner": "example_org", 
  "repo_name": "example_repo",
  "async_execution": true,
  "tenant_id": "tenant_123"
}
```

#### Workflow Status
```bash
GET /status/{workflow_id}
```

#### Health Checks
```bash
GET /health                    # Basic health check
GET /health/detailed          # Detailed health check
```

### Direct Orchestrator Usage

```python
from app.orchestrator import DatabaseDecommissionOrchestrator
from app.models import WorkflowConfig
from app.utils import create_logger_for_workflow

# Configure workflow
config = WorkflowConfig(
    database_name="postgres_air",
    repo_owner="example_org",
    repo_name="example_repo",
    tenant_id="tenant_123",
    user_id="user_456",
    max_parallel_steps=4,
    debug_mode=True
)

# Create logger
logger = create_logger_for_workflow(
    workflow_id="custom_workflow", 
    database_name=config.database_name,
    tenant_id=config.tenant_id
)

# Execute workflow
orchestrator = DatabaseDecommissionOrchestrator(
    config=config,
    logger=logger
)

result = await orchestrator.execute_workflow()
print(f"Workflow completed: {result.success}")
```

## Configuration

### Workflow Configuration

```python
WorkflowConfig(
    database_name="target_database",      # Required: Database to decommission
    repo_owner="github_owner",           # Required: GitHub repository owner
    repo_name="repository_name",         # Required: GitHub repository name
    tenant_id="tenant_id",               # Optional: Manager tenant ID
    user_id="user_id",                   # Optional: Manager user ID
    max_parallel_steps=4,                # Optional: Max parallel workflow steps
    default_timeout=120,                 # Optional: Default step timeout (seconds)
    debug_mode=False                     # Optional: Enable debug logging
)
```

### Manager Integration Settings

- **Database Client**: Automatically configured from Manager's `MONGO_DB_URI`
- **Azure OpenAI**: Configured from Manager's Azure OpenAI settings
- **Celery Integration**: Optional, for asynchronous workflow execution
- **Tenant Context**: Automatically applied to all operations when provided

### Quality Thresholds

Configurable quality gates and thresholds:
- **File Coverage**: 80% (minimum files discovered vs repository total)
- **Pattern Accuracy**: 85% (confidence in pattern matching)
- **Reference Completeness**: 90% (completeness of reference detection)
- **Validation Consistency**: 95% (consistency across validation rules)

## Testing

### Test Suite Structure

```bash
tests/
├── conftest.py                 # Test fixtures and configuration
├── pytest.ini                 # Test runner settings
├── unit/                       # Unit tests
│   ├── test_models.py         # Data model tests
│   ├── test_utils.py          # Utility function tests
│   ├── test_validation_rules.py # Business rule tests
│   ├── test_orchestrator.py   # Orchestrator tests
│   └── test_api_routes.py     # API endpoint tests
└── integration/                # Integration tests
    └── test_workflow_integration.py # End-to-end workflow tests
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Manager-specific tests
pytest -m manager

# Tenant-aware tests
pytest -m tenant

# With coverage
pytest --cov=app --cov-report=html

# Async tests only
pytest -m asyncio
```

### Test Categories

- `@pytest.mark.unit`: Fast, isolated unit tests
- `@pytest.mark.integration`: Component integration tests
- `@pytest.mark.asyncio`: Async functionality tests
- `@pytest.mark.manager`: Manager-specific feature tests
- `@pytest.mark.tenant`: Tenant-aware functionality tests
- `@pytest.mark.slow`: Performance/slow-running tests

## Monitoring and Observability

### Logging

Structured logging with Manager integration:
```python
from app.utils import create_logger_for_workflow

logger = create_logger_for_workflow(
    workflow_id="workflow_123",
    database_name="postgres_air", 
    tenant_id="tenant_123"
)

logger.log_workflow_start(config, metadata)
logger.log_step_start("validation", "Starting validation")
logger.log_info("Process completed", {"files_processed": 10})
logger.log_error("Validation failed", exception)
logger.log_workflow_end(result, success=True)
```

### Metrics

Integration with Manager's Prometheus metrics:
- Workflow execution times
- Success/failure rates
- Step completion rates
- Tenant-specific metrics
- Resource utilization

### Health Checks

Comprehensive health monitoring:
- Database connectivity
- Azure OpenAI availability
- MCP server status
- Celery worker status
- Memory and performance metrics

## Business Rules

### Validation Rules

1. **Database Reference Validation**
   - Scans all discovered files for database name references
   - Calculates reference density and risk scores
   - Provides tenant-specific analysis and recommendations

2. **Rule Compliance Validation**
   - Validates pattern discovery quality and confidence
   - Ensures sufficient analysis coverage
   - Checks compliance with discovery standards

3. **Service Integrity Validation**
   - Assesses impact on critical system files
   - Evaluates risk to service operations
   - Provides recovery complexity analysis

### Quality Rules

1. **File Coverage Gate**: Ensures comprehensive file discovery
2. **Pattern Accuracy Gate**: Validates pattern matching quality
3. **Reference Completeness Gate**: Confirms complete reference detection

### Risk Assessment

Multi-factor risk analysis:
- **File Impact Risk**: Based on file types and counts
- **Reference Density Risk**: Database reference concentration
- **Critical System Risk**: Impact on infrastructure components
- **Service Dependencies Risk**: Effect on service operations
- **Data Integrity Risk**: Database schema and integrity concerns
- **Rollback Complexity Risk**: Complexity of reversing changes
- **Tenant Impact Risk**: Tenant-specific impact analysis
- **Compliance Risk**: Regulatory and policy compliance

## Error Handling

### Graceful Degradation

The system is designed to continue operating with reduced functionality:
- **MCP Service Unavailable**: Falls back to cached data or simplified processing
- **Database Disconnection**: Continues with in-memory state management
- **AI Service Issues**: Uses fallback pattern matching algorithms
- **Network Issues**: Implements retry mechanisms with exponential backoff

### Error Recovery

- **Transient Failures**: Automatic retry with configurable attempts
- **Validation Failures**: Detailed error reporting with remediation suggestions
- **Workflow Interruption**: State preservation and resume capabilities
- **Resource Exhaustion**: Graceful handling with cleanup procedures

## Security Considerations

### Data Protection

- **Credential Masking**: Automatic masking of sensitive data in logs
- **Tenant Isolation**: Complete isolation between tenant workflows
- **Audit Logging**: Comprehensive audit trail for compliance
- **Input Validation**: Strict validation of all inputs and parameters

### Access Control

- **Tenant-Based Access**: Operations scoped to tenant permissions
- **User Context**: User identification preserved throughout workflow
- **API Authentication**: Integration with Manager's authentication system
- **Resource Permissions**: Proper authorization for external service access

## Performance Characteristics

### Scalability

- **Concurrent Workflows**: Support for multiple simultaneous executions
- **Resource Management**: Efficient memory and CPU utilization
- **Async Operations**: Non-blocking I/O for all external service calls
- **Caching**: Intelligent caching of repeated operations

### Performance Targets

- **Workflow Startup**: < 2 seconds
- **Pattern Discovery**: < 30 seconds for typical repositories
- **Validation Processing**: < 10 seconds for standard rule sets
- **API Response Time**: < 500ms for status and health endpoints
- **Memory Usage**: < 500MB per active workflow

## Troubleshooting

### Common Issues

1. **MCP Server Connection Failures**
   ```bash
   # Check MCP server configuration
   npx @modelcontextprotocol/server-github --version
   
   # Verify environment variables
   echo $GITHUB_TOKEN
   ```

2. **Database Connection Issues**
   ```bash
   # Test MongoDB connection
   mongosh $MONGO_DB_URI --eval "db.adminCommand('ping')"
   ```

3. **Azure OpenAI Authentication**
   ```bash
   # Verify Azure OpenAI configuration
   curl -H "Authorization: Bearer $AZURE_OPENAI_API_KEY" $AZURE_OPENAI_ENDPOINT
   ```

### Debug Mode

Enable debug mode for detailed logging:
```python
config = WorkflowConfig(
    database_name="postgres_air",
    repo_owner="example_org",
    repo_name="example_repo", 
    debug_mode=True  # Enables verbose logging
)
```

### Log Analysis

Key log entries to monitor:
- `workflow_start`: Workflow initiation
- `step_start`/`step_end`: Individual step execution
- `mcp_client_connect`: MCP server connections
- `validation_result`: Business rule outcomes
- `workflow_complete`: Final workflow status

## Contributing

### Development Setup

1. **Clone and Setup**:
   ```bash
   cd manager/src/usecases/database_decommissioning
   uv sync --dev
   ```

2. **Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

3. **Code Quality**:
   ```bash
   # Linting
   ruff check .
   
   # Type checking
   mypy app/
   
   # Formatting
   black app/ tests/
   ```

### Testing Requirements

- All new features must include unit tests
- Integration tests for major workflow changes
- Maintain minimum 80% test coverage
- All tests must pass before merging

### Code Style

- Follow Manager project conventions
- Use async/await for all I/O operations
- Comprehensive type hints
- Google-style docstrings
- Maximum 500 lines per file

## License

This code is part of the Manager project and follows the same licensing terms.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the test suite for usage examples
3. Consult the Manager project documentation
4. Open an issue in the Manager project repository