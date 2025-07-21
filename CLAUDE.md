# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

- **INITIAL.md**: Comprehensive feature specification with context engineering principles
- **INITIAL.template.md**: Template for creating new feature specifications  
- **CLAUDE.md**: This file - project-wide development guidance and patterns

Context engineering provides all necessary implementation details in INITIAL.md, eliminating the need for separate planning phases.

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

## CRITICAL RULE: Python Environment Management

**THERE IS ONLY ONE PYTHON VIRTUAL ENVIRONMENT: `<manager_project_root>/.venv`**

- **ALL Python code execution MUST use**: `/Users/bprzybysz/nc-src/ovora/manager/.venv/bin/python`
- **ALL pytest execution MUST use**: `cd /Users/bprzybysz/nc-src/ovora/manager && .venv/bin/python -m pytest`
- **NO other virtual environments are allowed** - not `uv run`, not tool-specific venvs, not conda, nothing else
- **ALL Python dependencies** for the entire manager project are managed through the single `pyproject.toml` at manager root
- **ALL microservice tools** (jira, confluence, etc.) dependencies are included in the manager's main environment
- **NO exceptions to this rule** - if something doesn't work, fix the imports/paths, don't create new environments

### Why This Rule Exists
- Ensures consistent dependency management across all components
- Prevents import path conflicts between different tools
- Simplifies testing and development workflows
- Maintains single source of truth for all Python dependencies