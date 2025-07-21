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

### DB Runbook Finder Workflow

- **Location**: `manager/src/usecases/db_runbook_finder/`
- **Purpose**: AI-powered database runbook discovery and semantic search using ChromaDB vector database
- **Features**: 
  - Semantic search with sentence-transformers embeddings
  - Confluence integration for runbook extraction
  - Comprehensive test data with 5 mock database runbooks
  - Full endpoint coverage testing (health, CRUD, search, bulk operations)
  - Job management for asynchronous bulk operations
  - Vector database persistence with ChromaDB
- **Testing**: `tests/` directory contains mock data, test utilities, and comprehensive endpoint tests
- **Integration**: Uses existing Confluence and Jira tools, GraphMCP framework patterns

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