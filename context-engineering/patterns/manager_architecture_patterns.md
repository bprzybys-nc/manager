# Manager Architecture Patterns

## Overview

This document captures architectural patterns and decisions specific to the Ovora Manager component. These patterns provide guidance for consistent development and integration across the Manager ecosystem.

## Core Architectural Patterns

### 1. Microservice Tool Architecture

**Pattern**: Isolated microservice tools with standardized APIs

```
Manager Core API
├── Tool: Confluence (Port 8000)
├── Tool: Jira (Port 8001)
├── Tool: CMD Exec (Port 8002)
└── Tool: DB Servers CMDB (Port 8003)
```

**Key Characteristics**:
- Each tool is a separate FastAPI service
- Independent deployment and scaling
- Standardized health checks and error handling
- Dockerized with individual pyproject.toml
- Common authentication patterns

**When to Use**:
- External service integrations (Slack, Jira, Confluence)
- Command execution and system operations
- Database and infrastructure management

**Implementation Pattern**:
```python
# Standard microservice structure
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI(title="Service Name", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/resource")
async def create_resource(data: BaseModel):
    # Service-specific implementation
    pass
```

### 2. GraphMCP Framework Integration

**Pattern**: Workflow orchestration using Multiple Model Context Protocol

```
Manager Component
├── GraphMCP Framework
│   ├── MCP Clients (GitHub, Slack, Repomix, Filesystem)
│   ├── Workflow Builder (Fluent API)
│   └── Context Management
└── Use Cases
    ├── Database Decommissioning
    └── DB Runbook Finder
```

**Key Characteristics**:
- Async-first workflow execution
- Multi-client orchestration
- Structured logging and monitoring
- Error handling with graceful degradation
- Context-aware state management

**When to Use**:
- Complex multi-step workflows
- Integration with multiple external services
- AI-powered automation tasks
- Repository analysis and management

**Implementation Pattern**:
```python
from frameworks.graphmcp.workflows.builder import WorkflowBuilder

workflow = (WorkflowBuilder("workflow_name", config_path)
    .with_config(max_parallel_steps=4, default_timeout=120)
    .step_auto("validate", "Validation", validate_step)  # PREFERRED
    .github_analyze_repo("analyze", repo_url)
    .slack_post("notify", channel_id, message)
    .build())
```

### 3. Use Case Architecture

**Pattern**: Domain-driven use case organization

```
src/usecases/
├── database_decommissioning/
│   ├── app/ (Application layer)
│   ├── orchestrator.py (Use case orchestration)
│   └── tests/ (Use case specific tests)
└── db_runbook_finder/
    ├── nodes.py (Workflow nodes)
    ├── workflow.py (Main workflow)
    └── tests/ (Test infrastructure)
```

**Key Characteristics**:
- Self-contained use case implementations
- Independent testing infrastructure
- Clear separation of concerns
- Dedicated configuration and dependencies

**When to Use**:
- Complex business workflows
- AI-powered analysis tasks
- Multi-step automation processes
- Domain-specific functionality

### 4. AI Integration Architecture

**Pattern**: Structured AI service integration with Azure OpenAI

```
AI Integration Layer
├── Configuration (Azure OpenAI)
├── Service Layer (Incident Analysis, Code Analysis)
├── Prompt Templates (Standardized prompts)
└── Response Parsing (Structured outputs)
```

**Key Characteristics**:
- Centralized AI configuration management
- Structured input/output models using Pydantic
- Retry logic and error handling
- Token usage tracking and monitoring
- Context-aware prompt engineering

**When to Use**:
- Incident analysis and response
- Code quality assessment
- Decision support systems
- Automated summarization and classification

**Implementation Pattern**:
```python
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

class AIResponse(BaseModel):
    success: bool
    content: str
    confidence: Optional[float]
    
async def analyze_with_ai(input_data: Dict) -> AIResponse:
    client = AzureChatOpenAI(...)
    response = await client.ainvoke(messages)
    return AIResponse.parse(response.content)
```

### 5. Database Pattern

**Pattern**: MongoDB with connection management

```
Database Layer
├── DatabaseClient (Connection management)
├── Collection-specific modules (Incidents, Inventory)
└── Query patterns (Aggregation, indexing)
```

**Key Characteristics**:
- Context manager for connection lifecycle
- Collection-specific access patterns
- Proper error handling and retry logic
- Environment-based configuration

**Implementation Pattern**:
```python
from src.database.client import DatabaseClient

async with DatabaseClient() as db:
    result = await db.incidents.find_one({"id": incident_id})
```

## Cross-Component Integration Patterns

### 1. Agent Integration Pattern

**Pattern**: API-based communication with Go Agent

```
Manager API ←→ Agent (Go binary)
├── REST endpoints for data collection
├── Metrics aggregation and storage
└── Health check and status reporting
```

**Key Characteristics**:
- RESTful API communication
- Standardized data formats
- Async processing for performance
- Comprehensive error handling

### 2. UI Integration Pattern

**Pattern**: API-first design for Streamlit UI

```
Manager API ←→ UI (Streamlit)
├── Data endpoints for dashboard visualization
├── Real-time updates via WebSocket/polling
└── Authentication and authorization
```

**Key Characteristics**:
- JSON API responses optimized for visualization
- Proper CORS configuration
- Authentication integration with Auth0
- Real-time data updates

## Configuration Management Patterns

### 1. Environment Configuration Pattern

**Pattern**: Centralized configuration with environment validation

```python
# src/config.py
from pydantic import BaseSettings

class Config(BaseSettings):
    # Required settings
    azure_openai_api_key: str
    azure_openai_endpoint: str
    mongo_db_uri: str
    
    # Optional settings with defaults
    prometheus_address: str = "http://localhost:9090"
    celery_broker_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

**Key Characteristics**:
- Environment variable validation
- Type safety with Pydantic
- Default values for optional settings
- Environment-specific configuration files

### 2. Microservice Configuration Pattern

**Pattern**: Independent configuration per microservice tool

```
tools/confluence/
├── pyproject.toml (Dependencies)
├── .env (Environment variables)
└── app/config.py (Service-specific config)
```

**Key Characteristics**:
- Service isolation
- Independent dependency management
- Service-specific environment variables
- Consistent configuration patterns across services

## Error Handling Patterns

### 1. Hierarchical Error Handling

**Pattern**: Structured exception hierarchy

```python
class ManagerError(Exception):
    """Base Manager exception"""
    pass

class DatabaseError(ManagerError):
    """Database operation errors"""
    pass

class AIServiceError(ManagerError):
    """AI service errors"""
    pass

class WorkflowError(ManagerError):
    """Workflow execution errors"""
    pass
```

### 2. Graceful Degradation Pattern

**Pattern**: Continue operation when non-critical services fail

```python
async def process_with_fallback():
    try:
        # Attempt primary processing
        result = await primary_service.process()
    except ServiceUnavailableError:
        # Fallback to cached or alternative processing
        logger.warning("Primary service unavailable, using fallback")
        result = await fallback_service.process()
    
    return result
```

## Monitoring and Observability Patterns

### 1. Structured Logging Pattern

**Pattern**: Consistent logging across all components

```python
import logging
from frameworks.graphmcp.graphmcp_logging import get_logger

logger = get_logger(
    workflow_id=f"workflow_{name}",
    config=LoggingConfig.from_env()
)

logger.log_workflow_start(params, config)
logger.log_step_start("step_name", "Description")
logger.log_step_end("step_name", result, success=True)
```

### 2. Metrics Collection Pattern

**Pattern**: Prometheus metrics integration

```python
from prometheus_client import Counter, Histogram

# Request metrics
requests_total = Counter(
    'manager_requests_total',
    'Total requests',
    ['service', 'method', 'status']
)

request_duration = Histogram(
    'manager_request_duration_seconds',
    'Request duration'
)
```

## Testing Patterns

### 1. Multi-Layer Testing Strategy

```
Testing Layers
├── Unit Tests (Fast, isolated)
├── Integration Tests (Component interaction)
├── Performance Tests (Load and timing)
└── E2E Tests (Complete workflows)
```

### 2. Mock and Fixture Patterns

```python
@pytest.fixture
def mock_database():
    mock_db = Mock()
    mock_db.fetch_all = AsyncMock(return_value=[])
    return mock_db

@pytest.fixture
async def async_client():
    async with httpx.AsyncClient() as client:
        yield client
```

## Security Patterns

### 1. Authentication and Authorization

**Pattern**: Layered security approach

```
Security Layers
├── API Key authentication for service-to-service
├── JWT tokens for user authentication
├── Role-based access control
└── Input validation and sanitization
```

### 2. Secrets Management

**Pattern**: Environment-based secrets with validation

```python
# No secrets in code
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key must be provided")

# Mask secrets in logs
logger.info(f"Using API key: {api_key[:4]}***")
```

## Performance Optimization Patterns

### 1. Async-First Architecture

**Pattern**: Async operations throughout the stack

```python
# Database operations
async with DatabaseClient() as db:
    result = await db.collection.find_one(query)

# HTTP requests
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# AI processing
response = await ai_client.ainvoke(messages)
```

### 2. Caching Strategy

**Pattern**: Multi-level caching

```
Caching Levels
├── Application cache (In-memory)
├── Redis cache (Distributed)
└── HTTP response caching
```

## Deployment Patterns

### 1. Containerized Deployment

**Pattern**: Docker containers with health checks

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen
COPY app/ ./app/
HEALTHCHECK CMD curl -f http://localhost:8000/health
CMD ["uv", "run", "uvicorn", "app.api:app", "--host", "0.0.0.0"]
```

### 2. Service Discovery Pattern

**Pattern**: Environment-based service discovery

```python
# Service endpoints from environment
CONFLUENCE_URL = os.getenv("CONFLUENCE_SERVICE_URL", "http://confluence:8000")
JIRA_URL = os.getenv("JIRA_SERVICE_URL", "http://jira:8001")
```

## Migration and Evolution Patterns

### 1. Backward Compatibility

**Pattern**: Versioned APIs with deprecation strategy

```python
@app.get("/api/v1/incidents")  # Deprecated
@app.get("/api/v2/incidents")  # Current
async def list_incidents():
    pass
```

### 2. Database Migration Pattern

**Pattern**: Scripted database migrations

```python
async def migrate_database():
    """Apply database migrations"""
    migrations = [
        "001_create_incidents_table",
        "002_add_incident_tags",
        "003_update_status_enum"
    ]
    
    for migration in migrations:
        await apply_migration(migration)
```

## Decision Records

### ADR-001: Microservice Tool Architecture
- **Decision**: Implement external integrations as separate microservices
- **Rationale**: Isolation, independent scaling, fault tolerance
- **Consequences**: Additional operational complexity, network latency

### ADR-002: GraphMCP Framework Adoption
- **Decision**: Use GraphMCP for complex workflow orchestration
- **Rationale**: Async support, multi-client coordination, structured logging
- **Consequences**: Learning curve, framework dependency

### ADR-003: MongoDB for Primary Storage
- **Decision**: MongoDB as primary database with structured collections
- **Rationale**: Document flexibility, async driver support, aggregation capabilities
- **Consequences**: NoSQL learning curve, consistency considerations

### ADR-004: Azure OpenAI Integration
- **Decision**: Azure OpenAI as primary AI service provider
- **Rationale**: Enterprise features, compliance, integration capabilities
- **Consequences**: Vendor lock-in, cost considerations

## Future Considerations

### Planned Evolutions
1. **Event-Driven Architecture**: Move towards event streaming with Apache Kafka
2. **GraphQL API**: Consider GraphQL for more flexible UI integration
3. **Service Mesh**: Implement Istio for advanced service communication
4. **Multi-Region Deployment**: Support for geographic distribution

### Technology Roadmap
- **Short Term**: Complete microservice extraction, enhance monitoring
- **Medium Term**: Implement event streaming, add GraphQL layer
- **Long Term**: Multi-region deployment, advanced AI capabilities

## References

### Internal Documentation
- GraphMCP Framework: `src/frameworks/graphmcp/README.md`
- API Documentation: `src/api.py` and individual tool APIs
- Configuration Guide: `src/config.py`

### External Resources
- FastAPI Documentation: https://fastapi.tiangolo.com/
- MongoDB Async Driver: https://motor.readthedocs.io/
- Azure OpenAI: https://docs.microsoft.com/en-us/azure/cognitive-services/openai/

### Architecture Influences
- Domain-Driven Design principles
- Microservices architecture patterns
- Async-first development practices
- Observable systems design