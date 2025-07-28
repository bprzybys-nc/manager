# Product Requirements Prompt (PRP): Database Decommissioning Workflow Migration

## Executive Summary

**Feature**: Database Decommissioning Workflow Migration from GraphMCP Framework to Manager Use Cases
**Priority**: High
**Complexity**: Medium
**Implementation Target**: Claude Sonnet 4
**Expected Implementation Time**: 1-2 iterations with comprehensive context engineering

## Comprehensive Context for AI Implementation

### Current Implementation Analysis

The database decommissioning workflow currently exists in `src/frameworks/graphmcp/concrete/db_decommission/` as a mature, production-ready system with:

**Key Components (Verified):**
- `__init__.py` - Main orchestration module (170 lines, well-structured exports)
- `data_models.py` - Comprehensive data models using dataclasses with proper serialization
- `workflow_steps.py` - Step implementations following GraphMCP patterns
- `validation_helpers.py` - Environment and workflow validation
- `pattern_discovery.py` - AI-powered file analysis using LLM integration
- `repository_processors.py` - GitHub and repository handling
- `client_helpers.py` - MCP client management
- `utils.py` - Workflow utilities and configuration management
- `rules/` - Business rules in markdown format

**Current Architecture Patterns:**
- Async-first design with proper error handling
- Dataclass-based models with timestamp tracking and serialization
- GraphMCP WorkflowBuilder integration
- Structured logging throughout
- Comprehensive test suite (unit/integration/e2e)
- CLI interface via `cli.py`

### Manager Component Integration Patterns

Based on analysis of existing Manager use cases:

**Use Case Structure Pattern (`src/usecases/db_incident_assistant/`):**
```
src/usecases/{use_case_name}/
├── pyproject.toml              # Independent dependencies
├── README.md                   # Use case documentation
├── app/                        # Application logic
│   ├── api.py                  # FastAPI routes
│   ├── main.py                 # Core logic
│   └── tests_*.py              # Tests
```

**Tool Structure Pattern (`src/tools/confluence/`):**
```
src/tools/{tool_name}/
├── pyproject.toml              # Tool dependencies
├── README.md                   # Tool documentation
├── app/                        # Application logic
│   ├── api.py                  # FastAPI routes
│   └── *.py                    # Core modules
├── tests/                      # Test structure
└── docker-compose.yml          # Local development
```

**Manager API Integration (`src/api.py`):**
```python
# Pattern for including routes
app.include_router(
    Route(db, clients, config).router, 
    prefix="/api/v1/path"
)
```

### Migration Architecture Strategy

**Recommended Target Structure:**
```
src/usecases/database_decommissioning/
├── pyproject.toml                      # Use case dependencies
├── README.md                           # Use case documentation
├── app/                                # Application logic
│   ├── __init__.py
│   ├── api.py                          # FastAPI routes for Manager integration
│   ├── workflow_orchestrator.py        # Main workflow coordination
│   ├── models.py                       # Migrated data models
│   ├── clients/                        # MCP client wrappers
│   │   ├── __init__.py
│   │   ├── github_client.py
│   │   ├── slack_client.py
│   │   └── repomix_client.py
│   ├── processors/                     # Processing engines
│   │   ├── __init__.py
│   │   ├── file_processor.py
│   │   ├── pattern_discovery.py
│   │   ├── repository_processor.py
│   │   └── validation_processor.py
│   ├── validation/                     # Validation logic
│   │   ├── __init__.py
│   │   ├── environment_validation.py
│   │   ├── workflow_validation.py
│   │   └── quality_assurance.py
│   └── utils.py                        # Workflow utilities
├── rules/                              # Business rules (migrated)
│   ├── decomission-refac-ruliade.md
│   └── quicksearchpatterns.md
└── tests/                              # Comprehensive test suite
    ├── conftest.py
    ├── pytest.ini
    ├── unit/
    ├── integration/
    └── e2e/
```

### FastAPI 2025 Best Practices Integration

Based on research, the migration should follow:

1. **Async-First Design**: All I/O operations use async/await
2. **Layered Architecture**: API, business logic, and data access layers
3. **Repository Pattern**: For data access abstraction
4. **Dependency Injection**: For service dependencies
5. **Modern Tooling**: Use `uv` for package management
6. **Security**: Proper authentication/authorization integration

## Implementation Blueprint

### Phase 1: Core Migration (Primary Focus)

**Step 1: Directory Structure Creation**
```bash
# Create target directory structure
mkdir -p src/usecases/database_decommissioning/{app/{clients,processors,validation},rules,tests/{unit,integration,e2e}}
```

**Step 2: Dependency Configuration**
Create `pyproject.toml` following Manager patterns:
```toml
[project]
name = "database_decommissioning"
version = "0.1.0"
description = "Database decommissioning workflow use case"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.6",
    "uvicorn>=0.34.0",
    "pydantic>=2.0.0",
    # GraphMCP framework dependencies
    "asyncio",
    "dataclasses",
    # Manager integration dependencies
    "pymongo>=4.11.0",
    "celery[redis]>=5.4.0",
]
```

**Step 3: Data Models Migration**
Migrate `data_models.py` to `app/models.py` with enhancements:
- Preserve all existing dataclasses
- Add FastAPI integration (BaseModel inheritance where needed)
- Enhance with Manager-specific fields (tenant_id, user_id, etc.)
- Maintain backward compatibility

**Step 4: Core Logic Migration**
Migrate workflow components:
- `workflow_steps.py` → `app/workflow_orchestrator.py`
- `pattern_discovery.py` → `app/processors/pattern_discovery.py`
- `repository_processors.py` → `app/processors/repository_processor.py`
- `validation_helpers.py` → `app/validation/workflow_validation.py`
- `utils.py` → `app/utils.py`

**Step 5: MCP Client Integration**
Create client wrappers in `app/clients/`:
- Extract MCP client logic from current implementation
- Create standardized client interfaces
- Maintain GraphMCP framework compatibility

**Step 6: FastAPI Route Implementation**
Create `app/api.py` with Manager integration:
```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

router = APIRouter()

@router.post("/workflows")
async def create_workflow(
    workflow_config: WorkflowConfig,
    # Add Manager auth dependency
) -> Dict[str, Any]:
    """Create new database decommissioning workflow."""
    pass

@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str
) -> Dict[str, Any]:
    """Get workflow execution status."""
    pass

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str
) -> Dict[str, Any]:
    """Execute database decommissioning workflow."""
    pass
```

### Phase 2: Manager Integration Enhancement

**Manager API Integration:**
Modify `src/api.py` to include new routes:
```python
from src.usecases.database_decommissioning.app.api import router as db_decommission_router

app.include_router(
    db_decommission_router, 
    prefix="/api/v1/usecases/database-decommissioning"
)
```

**Authentication Integration:**
Follow Manager's auth patterns from existing use cases.

**Monitoring Integration:**
Add Prometheus metrics and Manager logging integration.

### Implementation Requirements

**File Size Constraints:**
- Maximum 500 lines per file (current implementation complies)
- Split large files into logical modules

**Backward Compatibility:**
- Maintain all existing functionality
- Preserve GraphMCP framework integration
- Keep existing CLI interface functional

**Testing Requirements:**
- Migrate all existing tests
- Add Manager integration tests
- Maintain 80%+ coverage

**Documentation Requirements:**
- Create comprehensive README.md
- Document API endpoints (OpenAPI)
- Migration guide for existing users

## Critical Implementation Context

### GraphMCP Framework Dependencies

**Preserved Integrations:**
- WorkflowBuilder pattern: Continue using `from frameworks.graphmcp.workflows import WorkflowBuilder`
- MCP Clients: Maintain GitHubMCPClient, SlackMCPClient, RepomixMCPClient usage
- Context Management: Preserve workflow context and state management
- Logging System: Use GraphMCP structured logging

**Import Pattern Preservation:**
```python
# Maintain these imports for GraphMCP integration
from frameworks.graphmcp.workflows.builder import WorkflowBuilder
from frameworks.graphmcp.clients.github import GitHubMCPClient
from frameworks.graphmcp.clients.slack import SlackMCPClient
from frameworks.graphmcp.clients.repomix import RepomixMCPClient
from frameworks.graphmcp.graphmcp_logging import get_logger
```

### Manager Integration Patterns

**Configuration Management:**
Follow Manager's pattern from `src/config.py`:
```python
# Environment variable access
import os
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
MONGO_DB_URI = os.environ.get("MONGO_DB_URI")
```

**Database Integration:**
Use Manager's DatabaseClient pattern:
```python
from src.database.client import DatabaseClient
db_client = DatabaseClient({"uri": config.MONGO_DB_URI})
```

**Celery Integration:**
Follow Manager's task pattern for background processing:
```python
from celery import Celery
celery_app = Celery("database_decommissioning", broker=config.CELERY_BROKER_URL)
```

## Validation Gates (Executable)

### Syntax and Style Validation
```bash
cd manager && uv run ruff check --fix src/usecases/database_decommissioning/
cd manager && uv run mypy src/usecases/database_decommissioning/
```

### Unit Testing
```bash
cd manager && uv run pytest src/usecases/database_decommissioning/tests/unit/ -v --cov=src/usecases/database_decommissioning/app --cov-report=html
```

### Integration Testing
```bash
cd manager && uv run pytest src/usecases/database_decommissioning/tests/integration/ -v
```

### GraphMCP Framework Compatibility
```bash
cd manager/src/frameworks/graphmcp && make test-all
cd manager/src/frameworks/graphmcp && make demo
```

### Manager API Integration
```bash
cd manager && uv run uvicorn main:app --port 9123 --reload &
sleep 5
curl -f http://localhost:9123/api/v1/usecases/database-decommissioning/health || echo "API not accessible"
```

### End-to-End Workflow Validation
```bash
cd manager/src/usecases/database_decommissioning && python -m app.workflow_orchestrator --dry-run --database=test_db
```

## Risk Mitigation Strategies

### Import Path Management
- Create import compatibility layer if needed
- Test all import paths thoroughly
- Maintain backward compatibility during transition

### Configuration Migration
- Preserve all existing environment variables
- Add Manager-specific configurations gradually
- Test configuration loading in both contexts

### Functionality Preservation
- Migrate tests first to ensure behavior preservation
- Run parallel testing during migration
- Validate all workflow steps individually

## Success Criteria Validation

**Functional Validation:**
- [ ] All existing workflow functionality preserved
- [ ] New Manager API endpoints operational
- [ ] GraphMCP framework integration maintained
- [ ] CLI interface continues working
- [ ] All tests passing

**Technical Validation:**
- [ ] Code quality metrics maintained (ruff, mypy)
- [ ] Test coverage ≥80%
- [ ] Performance characteristics preserved
- [ ] Memory usage within Manager constraints
- [ ] FastAPI best practices followed

**Integration Validation:**
- [ ] Manager authentication working
- [ ] Prometheus metrics collection active
- [ ] MongoDB integration functional
- [ ] Slack notifications operational
- [ ] GitHub operations preserved

## Implementation Task Sequence

1. **Create directory structure and pyproject.toml**
2. **Migrate data models with Manager enhancements**
3. **Migrate core workflow logic**
4. **Create MCP client wrappers**
5. **Implement FastAPI routes**
6. **Migrate and enhance test suite**
7. **Update Manager API integration**
8. **Create comprehensive documentation**
9. **Validate all functionality**
10. **Clean up old location (separate task)**

## External Resources for Implementation

- **FastAPI Best Practices 2025**: https://github.com/zhanymkanov/fastapi-best-practices
- **FastAPI Microservices Guide**: https://blog.devops.dev/building-enterprise-python-microservices-with-fastapi-in-2025-1-10-introduction-c1f6bce81e36
- **AsyncIO Best Practices**: https://www.nucamp.co/blog/coding-bootcamp-backend-with-python-2025-python-in-the-backend-in-2025-leveraging-asyncio-and-fastapi-for-highperformance-systems

## Quality Assurance Checklist

- [ ] All validation gates pass
- [ ] Code follows Manager conventions
- [ ] GraphMCP integration preserved
- [ ] Documentation complete and accurate
- [ ] Performance benchmarks met
- [ ] Security requirements satisfied
- [ ] Migration guide created
- [ ] Rollback plan documented

## Confidence Score: 9/10

This PRP provides comprehensive context for successful one-pass implementation:
- ✅ Complete analysis of current implementation
- ✅ Detailed Manager integration patterns
- ✅ Executable validation gates
- ✅ Clear task sequence
- ✅ Risk mitigation strategies
- ✅ External resources included
- ✅ GraphMCP compatibility preserved
- ✅ FastAPI 2025 best practices
- ✅ Comprehensive testing strategy

The implementation should succeed with minimal iterations due to the thorough context engineering approach.