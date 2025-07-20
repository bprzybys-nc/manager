# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context Engineering Enabled

This project uses **Context Engineering** - a systematic approach to providing AI assistants with comprehensive, structured context for dramatically improved code generation and implementation accuracy. This is 10x better than prompt engineering and 100x better than basic AI coding.

### Context Engineering Workflow

1. **Feature Request**: Start with detailed `INITIAL.md` template
2. **Research**: Use `/research <feature_area>` to understand existing patterns
3. **Examples**: Use `/examples <pattern_type>` to find relevant patterns
4. **PRP Creation**: Use `/prp <feature_name>` to create comprehensive Product Requirements Prompt
5. **Implementation**: Use `/implement PRPs/active/<feature_name>.md` for structured implementation
6. **Validation**: Use `/validate <feature_name>` for thorough validation

### Manager-Specific Context Assembly

The Manager component uses specialized context assembly patterns:

- **Comprehensive Component Context**: Full understanding of Manager architecture, GraphMCP framework, and microservices patterns
- **Cross-Component Integration**: Detailed knowledge of Agent (Go) and UI (Streamlit) integration requirements
- **AI-Powered Workflows**: Context for Azure OpenAI, LangChain, and GraphMCP workflow development
- **Database Patterns**: MongoDB interaction patterns and collection management
- **Tool Development**: Microservice tool patterns for external integrations
- **Performance Requirements**: Response time, resource usage, and scalability considerations
- **Security Context**: Authentication, authorization, and data protection patterns

### Context Engineering Commands

- `/research <topic>` - Analyze codebase patterns and architecture
- `/examples <pattern_type>` - Extract relevant code patterns
- `/prp <feature_name>` - Create comprehensive implementation blueprint
- `/implement <prp_file>` - Execute implementation with full context
- `/validate <feature_name>` - Validate implementation against requirements
- `/context <feature_request>` - Assemble comprehensive context

See `context-engineering/commands/` for detailed command documentation.

## Project Overview

SysAIdmin (Ovora) is an AI-powered system administration platform with three main components:

1. **Manager** (Python/FastAPI): Backend API with AI capabilities, task queue, and Slack integration
2. **Agent** (Go): Lightweight monitoring agent deployed on target machines
3. **UI** (Streamlit): Web dashboard for visualization and interaction

### Manager Component Architecture

The Manager is the core orchestration component featuring:
- **GraphMCP Framework**: Sophisticated workflow orchestration for code analysis and automation
- **Microservices Tools**: Individual FastAPI services for specific integrations
- **AI Integration**: Azure OpenAI with LangChain/LangGraph for intelligent automation
- **Task Processing**: Celery-based background task processing with Redis
- **Database**: MongoDB for persistent storage with structured collections

## Core Architecture

### Service Architecture
- **Manager**: Microservices-based with independent processes:
  - `main.py` → API service (FastAPI, port 9123)
  - `worker_main.py` → Celery worker for background tasks
  - `slack_main.py` → Slack integration worker
- **Agent**: Single Go binary with periodic data collection
- **UI**: Streamlit app with Auth0 authentication

### Data Flow
- Agents → Manager API → MongoDB (storage)
- Manager → Prometheus (metrics) → UI (visualization)
- Manager → Slack (notifications) → Users
- Manager → Azure OpenAI (AI processing) → Tools execution

### Cross-Component Integration

The Manager component maintains compatibility and integration with:

#### Agent Component (Go)
- **API Contracts**: RESTful endpoints for data collection and monitoring
- **Data Formats**: Structured JSON for metrics, system information, and health status
- **Authentication**: Secure API token-based authentication
- **Deployment**: Independent deployment with configurable Manager endpoints

#### UI Component (Streamlit)
- **API Endpoints**: Complete REST API for dashboard functionality
- **Real-time Data**: WebSocket or polling-based live updates
- **Authentication**: Auth0 integration with session management
- **Data Models**: Consistent Pydantic models for UI consumption

#### External Services
- **Atlassian Integration**: Confluence and Jira via dedicated microservice tools
- **GitHub Operations**: Repository management through GraphMCP framework
- **Slack Notifications**: Real-time messaging and interactive workflows
- **Azure Services**: OpenAI integration and cloud resource management

## Development Environment Setup

### Prerequisites
- Python 3.12 or higher (required)
- uv package manager for Python dependencies
- Docker/Podman for infrastructure services

### Manager Quick Start
```bash
# Setup Manager development environment
cd manager
uv sync                                    # Install dependencies
uv run uvicorn main:app --port 9123 --reload  # Run API
uv run celery -A worker_main worker --loglevel=info  # Run worker
uv run celery -A worker_main beat --loglevel=info    # Run scheduler
uv run python slack_main.py               # Run Slack worker
```

### GraphMCP Framework Development
```bash
# Setup GraphMCP framework
cd manager/src/frameworks/graphmcp
make setup                      # Install dependencies and setup environment
source .venv/bin/activate      # Activate virtual environment

# Verify installation
make test-all                  # Run all tests
make demo                      # Run demo workflow (mock mode)
```

### Common Development Commands
```bash
# Manager Development
cd manager
uv run pytest                            # Run all tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only
uv run pytest -k "test_specific"        # Run specific test

# GraphMCP Development
cd manager/src/frameworks/graphmcp
make dev                       # Full development environment setup
make test-unit                 # Unit tests only
make test-integration          # Integration tests only
make test-e2e                  # End-to-end tests (requires MCP servers)
make lint                      # Code linting with ruff and mypy
make format                    # Code formatting with black

# Demos & UI
make demo-real                 # Demo with live MCP services (~5-10min)
make demo-mock                 # Demo with cached data (~30s)
make preview-streamlit         # Start live workflow UI on port 8501
make cmp                       # Complete database decommissioning workflow
```

### Cross-Project Development Commands

#### Agent (Go)
```bash
cd ../agent  # From manager directory
go build -o sysaidmin_agent               # Build binary
./sysaidmin_agent -config=config.json    # Run with config

# Note: Requires Node Exporter running on target machines
# Basic config.json structure:
# {
#   "instance_id": "",                                        // UUID4 (auto-generated)
#   "manager_api_url": "http://localhost:9123",               // Manager API URL
#   "tick_seconds": 10,                                       // Data collection interval
#   "node_exporter_endpoint": "http://localhost:9100/metrics" // Node Exporter endpoint
# }
```

#### UI (Streamlit)
```bash
cd ../ui  # From manager directory
uv sync                                   # Install dependencies
uv run streamlit run app.py              # Run dashboard

# Required environment variables:
# API_URL=http://localhost:9123           # Manager API URL
# PROMETHEUS_URL=http://localhost:9090/api/v1  # Prometheus API URL

# Auth0 configuration required in ui/.streamlit/secrets.toml
# (see ui/.streamlit/secrets.toml.example for template)
```

### Development Environment Infrastructure
```bash
# Start infrastructure services (from manager directory)
docker-compose up -d                     # MongoDB, Redis, Prometheus

# Alternative infrastructure setup (using podman)
podman run -d -p 27017:27017 --name mongo mongo
podman run -d -p 6379:6379 --name redis redis
podman run -d -p 9090:9090 -v $(pwd)/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml --name prom prom/prometheus
```

## Project Architecture

### Manager Framework Structure
```
manager/
├── src/
│   ├── frameworks/
│   │   └── graphmcp/              # GraphMCP workflow framework
│   │       ├── clients/           # MCP client implementations
│   │       │   ├── base.py       # Abstract base class with async context manager
│   │       │   ├── github.py     # GitHub repository operations
│   │       │   ├── slack.py      # Slack notifications
│   │       │   ├── repomix.py    # Repository packaging and analysis
│   │       │   └── filesystem.py # File system operations
│   │       ├── workflows/         # Workflow orchestration engine
│   │       │   ├── builder.py    # Fluent API for workflow construction
│   │       │   ├── context.py    # Shared state management
│   │       │   └── ruliade/      # Rule-based workflow patterns
│   │       ├── concrete/          # Domain-specific implementations
│   │       │   ├── db_decommission/  # Database decommissioning workflow
│   │       │   └── preview_ui/    # Streamlit visualization
│   │       ├── utils/             # Reusable utilities
│   │       ├── graphmcp_logging/  # Structured logging system
│   │       └── tests/            # Comprehensive test suite
│   ├── tools/                     # Microservice integrations
│   │   ├── confluence/           # Atlassian Confluence integration
│   │   ├── jira/                 # Atlassian Jira integration
│   │   ├── cmd_exec/             # Command execution service
│   │   └── db_servers_cmdb/      # Database server CMDB
│   ├── modules/                   # Core business logic
│   ├── usecases/                  # Use case implementations
│   └── api.py                     # Main API routes
├── main.py                        # API service entry point
├── worker_main.py                 # Celery worker entry point
└── slack_main.py                  # Slack integration worker
```

### Key Architectural Patterns

#### MCP Client Architecture
- **Abstract Base Class**: All clients inherit from `BaseMCPClient`
- **Server Name Pattern**: Each client defines `SERVER_NAME` class attribute
- **Async Context Manager**: Full `async with` support for resource management
- **Error Handling**: Custom exception hierarchy (`MCPConnectionError`, `MCPToolError`)

#### Workflow Builder Pattern (Fluent API)
```python
workflow = (WorkflowBuilder("workflow_name", config_path)
    .with_config(max_parallel_steps=4, default_timeout=120)
    .step_auto("validate", "Validation", validate_step)  # PREFERRED
    .github_analyze_repo("analyze", repo_url)
    .slack_post("notify", channel_id, message)
    .build())
```

**Step Method Preference (in order):**
1. `step_auto()` - **PREFERRED** - Automatically wraps functions to match step signature
2. `step()` - Generic step method with delegate parameter
3. `custom_step()` - Legacy method, avoid unless necessary

#### Multi-Client Orchestration Pattern
```python
# Standard pattern for coordinating multiple MCP clients
github_client = GitHubMCPClient(context.config.config_path)
slack_client = SlackMCPClient(context.config.config_path)
repomix_client = RepomixMCPClient(context.config.config_path)

# Cache clients in workflow context
context._clients['ovr_github'] = github_client
context._clients['ovr_slack'] = slack_client
context._clients['ovr_repomix'] = repomix_client
```

### Configuration Management

#### Manager Configuration
- Environment variables centralized in `src/config.py`
- Required variables: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `MONGO_DB_URI`, `PROMETHEUS_ADDRESS`
- Optional: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`

#### MCP Server Configuration
Edit `src/frameworks/graphmcp/mcp_config.json` to configure MCP servers:
```json
{
  "mcpServers": {
    "ovr_github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$TOKEN"}
    },
    "ovr_slack": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-slack"],
      "env": {"SLACK_BOT_TOKEN": "$TOKEN"}
    }
  }
}
```

#### Environment Variables
- **Configuration Precedence**: `.env` → `secrets.json` → system environment
- **Variable Substitution**: Supports `${VAR_NAME}` syntax in configuration files
- **Required for Complete Workflows**: `GITHUB_TOKEN`, `SLACK_BOT_TOKEN` (optional)

### Database Patterns
- **Primary**: MongoDB via `DatabaseClient` wrapper
- **Collections**: incidents, inventory, tasks, questions, checkpoints
- **Connection**: Context manager pattern with proper cleanup

### AI Integration
- **Backend**: Azure OpenAI with LangChain/LangGraph
- **Monitoring**: Langfuse for observability
- **Tools**: Structured tool definitions for agent actions

### Microservices Tools
- Each tool is a separate FastAPI service with own `pyproject.toml`
- Examples: `src/tools/confluence/`, `src/tools/db_servers_cmdb/`
- Pattern: Dockerized services with standardized API

### Task Processing
- **Queue**: Celery with Redis broker
- **Key tasks**: `run_incident_assistant`, `scheduler.analyze_free_space`
- **Monitoring**: Prometheus metrics for task performance

## Testing Framework

### Test Structure & Markers
```bash
# Manager tests
cd manager
uv run pytest -m unit                # Unit tests only
uv run pytest -m integration         # Integration tests only
uv run pytest -m "not e2e"          # Skip E2E tests
uv run pytest -k "test_specific"    # Run specific test pattern

# GraphMCP tests
cd manager/src/frameworks/graphmcp
pytest -m unit                      # Unit tests only
pytest -m integration               # Integration tests only
pytest -m e2e                       # End-to-end tests
pytest -m "not e2e"                # Skip E2E tests
```

### Test Categories
- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Component interaction testing
- **E2E Tests**: Full workflow validation with real MCP servers
- **Performance Tests**: Resource management and timing tests

### Test Configuration
- **Coverage Requirement**: 80% minimum coverage
- **Async Support**: `pytest-asyncio` with `asyncio_mode = "auto"`
- **Fixtures**: Mock and real configurations in `conftest.py`

## Code Style & Conventions

### Core Principles
- **File Size Limit**: Maximum 500 lines per file
- **Async-First**: All I/O operations use `async`/`await`
- **Type Safety**: Comprehensive type hints throughout
- **Single Responsibility**: Each module has one clear purpose

### Data Models
```python
@dataclass
class WorkflowResult:
    success: bool
    duration_seconds: float
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WorkflowResult':
        return cls(**data)
```

### Async Context Manager Pattern
```python
class MCPClient:
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
```

### Structured Logging Pattern
```python
from graphmcp_logging import get_logger, LoggingConfig

config = LoggingConfig.from_env()
logger = get_logger(workflow_id=f"workflow_{name}", config=config)

logger.log_workflow_start(params, config)
logger.log_step_start("step_name", "Description...")
logger.log_table("Results", table_data)
logger.log_step_end("step_name", result, success=True)
```

## Specialized Components

### GraphMCP Framework
- **Location**: `src/frameworks/graphmcp/`
- **Purpose**: Shared workflow framework for AI-driven automation workflows
- **Features**: Pattern discovery, GitHub integration, workflow orchestration, MCP client coordination
- **Usage**: Available for all use cases via `from frameworks.graphmcp import ...`
- **Development**: `cd src/frameworks/graphmcp && make setup && make demo`

#### Core Architecture
```
GraphMCP Framework
├── clients/                    # MCP client implementations
│   ├── base.py                # Abstract base client with connection management
│   ├── github.py              # GitHub repository operations
│   ├── slack.py               # Slack notifications
│   ├── repomix.py             # Repository packaging and analysis
│   └── filesystem.py          # File system operations
├── workflows/                  # Workflow orchestration engine
│   ├── builder.py             # Fluent API for workflow construction
│   ├── context.py             # Shared state management
│   └── ruliade/               # Rule-based workflow patterns
├── concrete/                   # Concrete workflow implementations
│   ├── db_decommission/       # Database decommissioning workflow
│   ├── file_decommission_processor.py  # File processing engine
│   └── pattern_discovery.py   # AI-powered pattern detection
├── utils/                      # Reusable utilities
│   ├── parameter_service.py   # Configuration management
│   ├── monitoring.py          # System monitoring
│   └── error_handling.py      # Error handling system
└── graphmcp_logging/           # Structured logging system
```

#### Key Patterns for Future Workflows

**1. Multi-Client Orchestration Pattern**
```python
# Standard pattern for coordinating multiple MCP clients
github_client = GitHubMCPClient(context.config.config_path)
slack_client = SlackMCPClient(context.config.config_path)
repomix_client = RepomixMCPClient(context.config.config_path)

# Cache clients in workflow context
context._clients['ovr_github'] = github_client
context._clients['ovr_slack'] = slack_client
context._clients['ovr_repomix'] = repomix_client
```

**2. Fluent Workflow Builder Pattern**
```python
workflow = (WorkflowBuilder("workflow_name", config_path)
    .with_config(max_parallel_steps=4, default_timeout=120)
    .step_auto("validate", "Validation", validate_step)  # PREFERRED
    .github_analyze_repo("analyze", repo_url)
    .slack_post("notify", channel_id, message)
    .build())
```

**Step Method Preference Order:**
1. `step_auto()` - **PREFERRED** - Automatically wraps functions to match step signature
2. `step()` - Generic step method with delegate parameter
3. `custom_step()` - Legacy method, avoid unless necessary

**3. Strategy-Based File Processing Pattern**
```python
def _determine_strategy(self, file_path: Path) -> str:
    if file_path.suffix in ['.tf']:
        return 'infrastructure'
    elif file_path.suffix in ['.yml', '.yaml']:
        return 'configuration'
    elif file_path.suffix in ['.py', '.sh']:
        return 'code'
    return 'documentation'
```

**4. Graceful Degradation with Caching**
```python
try:
    existing_data = load_cached_data(key, logger)
    if existing_data:
        logger.log_info(f"Using cached data for {key}")
        return existing_data
    else:
        # Fallback to real processing
        result = await client.process_data(params)
        save_to_cache(result, key, logger)
        return result
except Exception as e:
    logger.log_error(f"Processing failed", exception=e)
    return {"success": False, "error": str(e)}
```

**5. MCP Server Configuration Pattern**
```json
{
  "mcpServers": {
    "ovr_github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$TOKEN"}
    },
    "ovr_slack": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-slack"],
      "env": {"SLACK_BOT_TOKEN": "$TOKEN"}
    }
  }
}
```

**6. Structured Logging Pattern**
```python
from graphmcp_logging import get_logger, LoggingConfig

config = LoggingConfig.from_env()
logger = get_logger(workflow_id=f"workflow_{name}", config=config)

logger.log_workflow_start(params, config)
logger.log_step_start("step_name", "Description...")
logger.log_table("Results", table_data)
logger.log_step_end("step_name", result, success=True)
```

**Development Commands**:
```bash
# Setup framework
cd src/frameworks/graphmcp
make setup                      # Install dependencies
make test-all                   # Run all tests
make demo                       # Run demo workflow

# Run specific workflows
make cmp DB=postgres_air        # Complete DB decommissioning
python run_workflow.py --name workflow_name --config mcp_config.json
```

### Database Decommissioning Workflow
Production-ready workflow for AI-driven database decommissioning:

```bash
# Run complete database decommissioning
cd src/frameworks/graphmcp
make cmp                           # Default: postgres_air database
make cmp DB=chinook               # Custom database
make cmp DB=chinook REPO=https://github.com/org/repo  # Custom DB + repo

# Start decommissioning UI
make db-decommission-ui           # Streamlit UI on port 8502
```

**Key Features:**
- Multi-repository processing with GitHub integration
- AI-powered pattern discovery using Repomix
- Contextual rules engine for intelligent file processing
- Quality assurance with automated validation
- Slack notifications with progress tracking

### Live Workflow Streaming
```bash
# Start live workflow visualization
cd src/frameworks/graphmcp
make preview-streamlit            # Start Streamlit UI on port 8501
make preview-demo                 # Complete demo (MCP server + UI)
```

### Atlassian Integrations

#### Confluence Tool
- **Location**: `src/tools/confluence/`
- **Main Client**: `app/confluence.py` - Core Confluence REST API client
- **Features**: 
  - Full page management (CRUD operations)
  - Vector search with ChromaDB integration
  - Bulk processing with background jobs
  - Attachment management
  - Health monitoring and detailed status checks
  - Runbook content processing and categorization
- **Dependencies**: `atlassian-python-api>=3.41.0`, `chromadb>=0.4.0`, `sentence-transformers>=2.2.0`

**API Endpoints**:
- `GET/PUT/DELETE/POST /pages/{page_id}` - Page management
- `GET /search` - Text-based search
- `POST /search/vector` - Semantic vector search
- `POST /bulk/process` - Start bulk processing job
- `GET /jobs/{job_id}` - Job status tracking
- `POST /pages/{page_id}/attachments` - Upload attachments
- `GET /health/detailed` - System health check

**Environment Variables**:
- `CONFLUENCE_URL` - Confluence instance URL
- `CONFLUENCE_USERNAME` - Username/email for authentication
- `CONFLUENCE_API_TOKEN` - API token for authentication
- `CONFLUENCE_TIMEOUT` - Request timeout (optional, default: 30s)

#### Jira Tool
- **Location**: `src/tools/jira/`
- **Main Client**: `app/jira.py` - Jira REST API client using `python-jira`
- **Features**:
  - Ticket lifecycle management
  - Rich text formatting in comments (bold, italic, code, code blocks)
  - Workflow state transitions
- **Dependencies**: `jira>=3.6.0`

**API Endpoints**:
- `GET /tickets/{ticket_id}` - Retrieve ticket with description and comments
- `POST /tickets/{ticket_id}/comments` - Add formatted comment to ticket
- `PUT /tickets/{ticket_id}` - Close ticket (optionally with comment)

**Environment Variables**:
- `JIRA_URL` - Jira instance URL
- `JIRA_USERNAME` - Username/email for authentication
- `JIRA_API_TOKEN` - API token for authentication

**Authentication**: Both tools use HTTP Basic Auth with username/email and API tokens

**Development Commands**:
```bash
# Confluence tool
cd src/tools/confluence
uv sync && uv run uvicorn app.api:app --port 8000 --reload

# Jira tool
cd src/tools/jira
uv sync && uv run uvicorn app.api:app --port 8001 --reload
```

### Slack Integration
- **Worker**: `slack_main.py`
- **Features**: Real-time notifications, interactive commands
- **Dependencies**: slack-bolt

## Development Workflow

### Package Management
- **Python components**: Use `uv` (modern pip replacement)
- **Go components**: Standard `go mod` with version pinning (in ../agent)
- **Dependencies**: Isolated per component

### Testing Strategy
- **Framework**: pytest with comprehensive configuration
- **Categories**: Unit, integration, performance, E2E (via markers)
- **Coverage**: Enabled with HTML reports
- **Configuration**: `pytest.ini` files in relevant directories

### Code Organization
- **Modular structure**: Clear domain separation (`modules/`, `tools/`, `usecases/`)
- **Database access**: Consistent patterns with dedicated DB classes
- **API structure**: FastAPI with router-based organization

## Important File Locations

### Configuration Files
- `pyproject.toml` - Python dependencies and project config
- `docker-compose.yaml` - Development infrastructure
- `../agent/go.mod` - Go dependencies (Agent component)
- `../ui/pyproject.toml` - UI dependencies

### Key Source Files
- `src/config.py` - Environment configuration
- `src/api.py` - Main API routes
- `src/database/client.py` - Database connection
- `src/llm/llm.py` - AI integration
- `../agent/sysaidmin_agent.go` - Agent main logic

### Testing
- `src/tests/` - Test suites
- `conftest.py` - Test configuration and fixtures
- `pytest.ini` - Test runner configuration

## Environment Variables

### Required
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `MONGO_DB_URI` - MongoDB connection string
- `PROMETHEUS_ADDRESS` - Prometheus server address (e.g., http://localhost:9090)
- `MANAGER_API_ADDRESS` - Manager API address for Prometheus targets (e.g., localhost:9123)

### Optional
- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_APP_TOKEN` - Slack app token
- `CELERY_BROKER_URL` - Redis URL (defaults to localhost)
- `METRICS_DIR` - Directory for metrics storage

### Atlassian Tools
- `CONFLUENCE_URL` - Confluence instance URL (e.g., https://your-domain.atlassian.net)
- `CONFLUENCE_USERNAME` - Username/email for Confluence authentication
- `CONFLUENCE_API_TOKEN` - API token for Confluence authentication
- `CONFLUENCE_TIMEOUT` - Request timeout (optional, default: 30s)
- `JIRA_URL` - Jira instance URL (e.g., https://your-domain.atlassian.net)
- `JIRA_USERNAME` - Username/email for Jira authentication
- `JIRA_API_TOKEN` - API token for Jira authentication

## Deployment

### Development
```bash
# Start all services (from manager directory)
docker-compose up -d     # Infrastructure
# Then start individual services as shown above
```

### Production
- **Kubernetes**: Helm charts in `../deployment/helm/`
- **Containers**: Containerfiles for manager and UI
- **Monitoring**: Prometheus integration configured

### Container Build and Deploy
```bash
# Manager container
docker build -t sysaidmin-manager -f Containerfile .
docker run \
  -e AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY} \
  -e AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT} \
  -e MONGO_DB_URI=${MONGO_DB_URI} \
  -e SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN} \
  sysaidmin-manager:latest
```

## Important Development Notes

### Virtual Environment
- **Always use venv**: `source .venv/bin/activate` before running Python commands (GraphMCP)
- **Package Management**: Uses `uv` for fast dependency management
- **Development Dependencies**: pytest, ruff, mypy, black automatically installed

### Error Handling
- **Graceful Degradation**: Workflows continue with caching when services fail
- **Retry Mechanism**: Exponential backoff for transient failures
- **Structured Exceptions**: Custom exception hierarchy for different failure types

### Performance Considerations
- **Connection Pooling**: MCP clients reuse connections
- **Caching Strategy**: Intelligent caching for repeated operations
- **Async Execution**: Parallel processing where possible

### Security
- **Credential Management**: Automatic credential masking in logs
- **Environment Isolation**: Secrets loaded from secure sources
- **Input Validation**: Comprehensive validation of all inputs

## Testing Philosophy

- **Unit tests**: Fast, isolated, no external dependencies
- **Integration tests**: Test component interactions
- **E2E tests**: Full workflow testing
- **Performance tests**: Resource usage and timing
- Use pytest markers to categorize tests appropriately

## Contributing Guidelines

### Before Making Changes
1. **Read existing code**: Follow established patterns and conventions
2. **Run tests**: `make test-all` to ensure nothing breaks
3. **Check code quality**: `make lint` and `make format`
4. **Add tests**: Unit tests required for new functionality

### File Organization
- **Modular Structure**: Group related functionality together
- **Clear Imports**: Use relative imports within packages
- **Documentation**: Comprehensive docstrings using Google style
- **Error Messages**: Clear, actionable error messages

### Performance & Reliability
- **Resource Management**: Always use async context managers
- **Error Recovery**: Implement graceful degradation strategies
- **Monitoring**: Add appropriate logging and metrics
- **Testing**: Include unit, integration, and E2E tests as appropriate

## Context Engineering Principles

This project follows context engineering principles for AI-assisted development:

### 1. Comprehensive Context Assembly

**Always provide complete context:**
- Reference existing patterns from `src/frameworks/graphmcp/examples/` directory
- Include architectural context and constraints
- Specify exact patterns to follow
- Provide detailed implementation requirements

**Example Context Assembly:**
```
When implementing a new MCP client:
1. Study src/frameworks/graphmcp/examples/mcp_client/base_client_pattern.py
2. Follow the SERVER_NAME class attribute pattern
3. Implement async context manager support
4. Use structured error handling from examples
5. Add comprehensive logging as shown in examples/logging/
```

### 2. Structured Feature Requests

**Use the INITIAL.md template for all feature requests:**
- Provide comprehensive feature descriptions
- Include business justification and success criteria
- Specify technical requirements and constraints
- Reference existing patterns and similar features
- Define clear acceptance criteria

**Template Sections:**
- Basic Information & Feature Description
- Functional & Technical Requirements
- Implementation Context & Existing Patterns
- Quality Requirements & Testing Strategy
- Acceptance Criteria & Risk Assessment

### 3. Product Requirements Prompts (PRPs)

**Create PRPs for all non-trivial features:**
- Research existing codebase patterns thoroughly
- Assemble comprehensive implementation context
- Provide detailed step-by-step implementation plan
- Include validation criteria and testing requirements
- Reference specific code examples and patterns

**PRP Structure:**
```
context-engineering/
├── PRPs/
│   ├── active/          # Currently active PRPs
│   ├── completed/       # Completed PRPs (archived)
│   ├── templates/       # PRP templates
│   └── examples/        # Example PRPs
└── commands/            # Context engineering commands
```

### 4. Pattern-Based Implementation

**Follow established patterns consistently:**
- **MCP Clients**: Use BaseMCPClient pattern with SERVER_NAME
- **Workflows**: Use WorkflowBuilder with step_auto() method
- **Logging**: Use structured logging with get_logger()
- **Testing**: Use pytest with appropriate markers
- **Error Handling**: Use custom exception hierarchies

**Pattern Discovery Process:**
1. Use `/research <feature_area>` to understand existing implementations
2. Use `/examples <pattern_type>` to find relevant patterns
3. Follow patterns exactly to maintain consistency
4. Add new patterns to examples/ directory when created

### 5. Validation Gates

**Implement comprehensive validation:**
- Code quality validation (lint, format, type-check)
- Functional validation (unit, integration, E2E tests)
- Performance validation (response time, throughput)
- Architecture validation (pattern compliance)
- Documentation validation (completeness, accuracy)

**Validation Commands:**
- `make lint` - Code quality validation
- `make test-all` - Comprehensive testing
- `make format` - Code formatting
- `/validate <feature_name>` - Full validation suite

### 6. Context Engineering Commands

**Use custom commands for structured development:**

**Research Commands:**
- `/research <topic>` - Comprehensive codebase analysis
- `/examples <pattern_type>` - Pattern extraction and documentation

**Implementation Commands:**
- `/prp <feature_name>` - Create Product Requirements Prompt
- `/implement <prp_file>` - Execute structured implementation
- `/context <feature_request>` - Assemble comprehensive context

**Validation Commands:**
- `/validate <feature_name>` - Comprehensive validation
- Standard make commands for specific validation types

### 7. Documentation-Driven Development

**Maintain comprehensive documentation:**
- Update CLAUDE.md with new patterns and conventions
- Document all patterns in examples/ directory
- Include usage examples and context in all documentation
- Update README.md with feature additions and changes

**Documentation Requirements:**
- All functions must have Google-style docstrings
- All patterns must be documented with examples
- All features must include usage examples
- All changes must update relevant documentation

### 8. Continuous Pattern Evolution

**Evolve patterns based on learnings:**
- Extract new patterns from successful implementations
- Update examples/ directory with new patterns
- Refine PRP templates based on experience
- Improve context engineering process continuously

**Pattern Evolution Process:**
1. Identify successful implementation patterns
2. Extract patterns into reusable examples
3. Update templates and documentation
4. Share patterns across the team
5. Continuously refine the process

### Context Engineering Benefits

Following these principles provides:
- **Predictable Results**: Consistent, high-quality implementations
- **Reduced Iterations**: Fewer implementation mistakes and rework
- **Knowledge Sharing**: Reusable patterns and comprehensive documentation
- **Faster Development**: Structured process with clear guidelines
- **Better Quality**: Comprehensive validation and testing
- **Maintainability**: Consistent patterns and thorough documentation

### Getting Started with Context Engineering

1. **Study the Examples**: Review `src/frameworks/graphmcp/examples/` directory thoroughly
2. **Practice the Workflow**: Use the full context engineering process
3. **Create Comprehensive PRPs**: Don't skip the detailed planning phase
4. **Follow Patterns Exactly**: Maintain consistency with existing code
5. **Validate Thoroughly**: Use all validation gates
6. **Document Everything**: Update examples and documentation

### Context Engineering vs. Traditional Approaches

| Aspect | Traditional Coding | Prompt Engineering | Context Engineering |
|--------|-------------------|-------------------|-------------------|
| **Success Rate** | 60-70% | 70-80% | 90-95% |
| **Consistency** | Variable | Moderate | High |
| **Maintainability** | Low | Low | High |
| **Knowledge Sharing** | Limited | Limited | Comprehensive |
| **Rework Required** | High | Moderate | Low |
| **Documentation** | Sparse | Moderate | Comprehensive |

Context engineering transforms AI-assisted development from unpredictable interactions into a systematic, reliable development methodology.