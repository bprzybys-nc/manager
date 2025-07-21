# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Scope and Boundaries

You have read-access to the entire repository to understand the full context. However, code modifications are strictly limited to the following designated areas:

Editable Directories:
src/usecases/database_decommissioning/
src/usecases/db_runbook_finder/
src/frameworks/graphmcp/

Read-Only Directories (Uless instructed otherwise like e.g. "I allow you to make changes in 'graphmcp'"):
All other directories, such as src/tools/, should be treated as stable, read-only libraries. You can and should use their functionality, but you must not alter their source code.


## Context Engineering Enabled

This project uses **Context Engineering** - a systematic approach to providing AI assistants with comprehensive, structured context for dramatically improved code generation and implementation accuracy. This is 10x better than prompt engineering and 100x better than basic AI coding.

### Context Engineering Workflow

1. **Feature Request**: Start with detailed `INITIAL.md` following context engineering template
2. **Research**: Manually research existing patterns and architecture
3. **Implementation**: Direct implementation using comprehensive context from INITIAL.md
4. **Validation**: Follow validation requirements specified in context documentation

**Note**: PLANNING.md and PRP-based workflows have been simplified to direct implementation using comprehensive INITIAL.md context specifications.

### Manager-Specific Context Assembly

The Manager component uses specialized context assembly patterns:

- **Comprehensive Component Context**: Full understanding of Manager architecture, GraphMCP framework, and microservices patterns
- **Cross-Component Integration**: Detailed knowledge of Agent (Go) and UI (Streamlit) integration requirements
- **AI-Powered Workflows**: Context for Azure OpenAI, LangChain, and GraphMCP workflow development
- **Database Patterns**: MongoDB interaction patterns and collection management
- **Tool Development**: Microservice tool patterns for external integrations
- **Performance Requirements**: Response time, resource usage, and scalability considerations
- **Security Context**: Authentication, authorization, and data protection patterns

### Context Engineering Files

**Core Documentation:**
- **CLAUDE.md**: This file - project-wide development guidance and patterns (c_instr)
- **INITIAL.md**: Comprehensive feature specification with context engineering principles (c_query)
- **INITIAL.template.md**: Template for creating new feature specifications (c_mem)

**Context Engineering System** (`context-engineering/`):
- **README.md**: Complete Manager context engineering system overview (c_instr)
- **examples/**: Implementation patterns and best practices library (c_know)
  - `graphmcp_workflow_patterns.py`: GraphMCP workflow implementation patterns
  - `manager_api_patterns.py`: Manager FastAPI patterns and best practices
  - `microservices_patterns.py`: Microservice tool patterns for external integrations
  - `ai_integration_patterns.py`: Azure OpenAI and LangChain integration patterns
  - `testing_patterns.py`: Comprehensive testing strategies and utilities
- **templates/**: Feature, workflow, and service development templates (c_mem)
  - `feature_request_template.md`: Manager-specific feature request template
  - `workflow_template.md`: GraphMCP workflow development template
  - `microservice_template.md`: Microservice tool development template
  - `integration_template.md`: External service integration template
- **commands/**: Context engineering workflow automation (c_tools)
  - `generate-prp.md`: PRP generation command with comprehensive research
  - `execute-prp.md`: PRP execution command for structured implementation
  - `run_demo.md`: Demo execution command for workflow testing
- **patterns/**: Architecture patterns and design decisions library (c_know)
  - `manager_architecture_patterns.md`: Manager-specific architecture patterns
- **validation/**: Quality assurance and validation framework (c_state)
  - `validate_context_engineering.py`: Comprehensive validation system
  - `final_validation.py`: Final quality assurance validation
  - `validate_consolidation.py`: Project consolidation validation
- **PRPs/**: Product Requirements Prompts for structured development (c_state)
  - `active/`: Work in progress PRPs
  - `completed/`: Completed and archived PRPs
  - `templates/`: PRP templates and examples
- **ARCHITECTURE.md**: Architecture decisions, design rationale, and evolution history (c_know)

**Coleman Context Engineering Framework Mapping:**
- **c_instr** (Instructions): `CLAUDE.md`, `context-engineering/README.md`
- **c_know** (Knowledge): `context-engineering/examples/`, `context-engineering/patterns/`, `ARCHITECTURE.md`
- **c_tools** (Tools): `context-engineering/commands/`, `.claude/` configuration
- **c_mem** (Memory): `context-engineering/templates/`, `INITIAL.template.md`
- **c_state** (State): `context-engineering/PRPs/`, `context-engineering/validation/`
- **c_query** (Query): `INITIAL.md` files, feature specifications

## Project Overview

SysAIdmin (Ovora) is an AI-powered system administration platform with three main components:

1. **Manager** (Python/FastAPI): Backend API with AI capabilities, task queue, and Slack integration
2. **Agent** (Go): Lightweight monitoring agent deployed on target machines
3. **UI** (Streamlit): Web dashboard for visualization and interaction

### Development Specifics

- **Python Logic Tests**: py logic tests are ran from project's root dir using .venv/bin/python
- **Keep Workflows' Tests**: keep workflowss' tests in their dir tests dir

### DB Runbook Finder Workflow - Production-Ready Implementation

**Location**: `manager/src/usecases/db_runbook_finder/`

**Purpose**: AI-powered database runbook discovery and semantic search using ChromaDB vector database with comprehensive mock data infrastructure for development and testing.

#### Core Features Implemented:
- **Semantic Search**: Vector embeddings with sentence-transformers (all-MiniLM-L6-v2 model)
- **ChromaDB Integration**: Persistent vector database with proper empty collection handling
- **Mock Confluence Layer**: Complete abstraction for offline development and CI/CD
- **Comprehensive API Coverage**: 20 endpoints with 100% test success rate
- **Job Management**: Asynchronous bulk operations with status tracking
- **Performance Validated**: <50ms response times for semantic search

#### Test Infrastructure Achievements:

**Mock Runbook Dataset** (`tests/data/`):
```
├── database_connection_runbook.json     # Connection troubleshooting
├── performance_monitoring_runbook.json  # Performance optimization  
├── backup_recovery_runbook.json        # Backup & disaster recovery
├── security_hardening_runbook.json     # Security & access control
├── migration_runbook.json              # Schema migrations
└── test_data_loader.py                 # Data management utilities
```

**Test Coverage** (100% success rate):
```python
# Example test pattern for endpoint validation
def test_semantic_search():
    response = client.get("/search/runbooks?query=database connection&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "processing_time" in data
    assert data["processing_time"] < 2.0  # Performance requirement
```

**ChromaDB Integration Patterns**:
- **Empty Collection Handling**: Fixed ChromaDB "Number of requested results 0" error
- **Vector Store Initialization**: Automatic collection setup with metadata indexing
- **Embedding Management**: Sentence transformers with dimension validation
- **Error Handling**: Graceful degradation when vector DB is unavailable

#### Mock Confluence Abstraction Layer:

**Design Philosophy**: Complete abstraction to enable seamless replacement with real Confluence API:

```python
# Mock data structure matches real Confluence API response format
{
  "metadata": {
    "title": "Database Connection Troubleshooting Runbook",
    "space_key": "RUNBOOKS", 
    "page_id": "123456",
    "url": "https://company.atlassian.net/wiki/spaces/RUNBOOKS/pages/123456",
    "tags": ["database", "troubleshooting", "connection"]
  },
  "procedures": [...],          # Structured runbook content
  "troubleshooting_steps": [...],
  "prerequisites": [...]
}
```

**Testing Patterns**:
- **Comprehensive Endpoint Coverage**: Health, CRUD, search, bulk ops, job management
- **Error Validation**: All 422/404/500 scenarios tested and working
- **Performance Testing**: Response time validation with specific thresholds
- **Mock Data Loading**: Reusable utilities for test data management

#### Key Discoveries & Solutions:

1. **ChromaDB Empty Collection Fix**: 
   ```python
   # Fixed: Handle empty collections gracefully
   collection_count = self._collection.count()
   if collection_count == 0:
       return []  # Don't query empty collection
   ```

2. **API Validation Fix**:
   ```python
   # Fixed: Proper HTTPException handling
   except HTTPException:
       raise  # Re-raise HTTP exceptions as-is
   except ValueError as e:
       raise HTTPException(status_code=422, detail=str(e))
   ```

3. **Routing Issue Resolution**:
   ```python
   # Test pattern for path parameter validation
   response = client.get("/runbooks/%20")  # URL-encoded whitespace
   assert response.status_code == 422  # Proper validation error
   ```

#### Integration Patterns:
- **GraphMCP Framework**: Multi-client orchestration patterns
- **Existing Tools**: Seamless integration with Confluence/Jira tools
- **Single Environment**: All dependencies managed in manager's .venv
- **Structured Logging**: Correlation IDs and comprehensive error tracking


## CRITICAL RULE: Unified Python Environment Management

### The Guiding Principle: One Project, One Environment

The `manager` project operates from a **single, unified virtual environment** located at the project root: `/.venv`. This environment contains all dependencies for the core application, all tools, and all use cases. There are no other virtual environments.

### How to Execute Code

There are two correct ways to run Python code, depending on the context:

**1. For Automation (`Makefile`, Scripts, CI/CD): Use `uv run`**

This is the preferred method for all automated tasks. `uv run` automatically detects and uses the project's `.venv` without requiring activation.

-   **To run a script:** `uv run python src/main.py`
-   **To run tests:** `uv run pytest`
-   **To run a tool:** `uv run ruff check .`

**2. For Interactive Development (Your Shell): Activate the Environment First**

When working directly in your terminal, activate the environment to ensure all commands use the correct interpreter and packages.

-   **Activation:** `source .venv/bin/activate`
-   **After activation, use standard commands:** `python`, `pytest`, `black`, etc.

*Under no circumstances should you use hardcoded paths like `/Users/bprzybysz/.../.venv/bin/python`.*

### How to Manage Dependencies

**The `pyproject.toml` at the project root is the single source of truth for all dependencies.**

-   **To install or update dependencies:** Run `uv sync` from the project root. This command will install everything specified in `pyproject.toml`.
-   **To add a new dependency:** Run `uv add `. This will add the package to `pyproject.toml` and install it.
-   **To add a new development dependency:** Run `uv add --dev `.

### Why This Unified Approach Is Critical

-   **Consistency**: Ensures all developers, scripts, and CI/CD pipelines use the exact same set of dependencies, eliminating "it works on my machine" issues.
-   **Simplicity**: Prevents a complex web of conflicting, nested virtual environments.
-   **Maintainability**: A single `pyproject.toml` file makes dependency updates and audits straightforward.
-   **Robust Tooling**: Aligns with the idiomatic usage of `uv`, making our `Makefile` and automation scripts cleaner and more reliable.