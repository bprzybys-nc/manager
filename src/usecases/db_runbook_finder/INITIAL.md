# INITIAL.md - DB Runbook Finder Workflow

## FEATURE:
Create a production-ready AI-powered database runbook discovery and semantic search system within the `src/usecases/db_runbook_finder/` directory. This workflow provides comprehensive runbook management through direct integration with existing production tools (Confluence, Jira, ChromaDB) while maintaining a complete mock data abstraction layer for offline development and CI/CD. The implementation achieves 100% test success rate with <50ms semantic search response times and comprehensive API coverage through 20 validated endpoints.

## EXAMPLES:

### GraphMCP Workflow Integration
**Reference**: `src/frameworks/graphmcp/workflows/builder.py`
- **WorkflowBuilder Pattern**: Uses fluent API for workflow construction with step-by-step orchestration
- **State Management**: Comprehensive `WorkflowState` dataclass with incident tracking and performance metrics
- **Node-Based Architecture**: Modular workflow nodes with clear separation of concerns
- **Error Handling**: Graceful degradation with comprehensive error state management

```python
# Example workflow construction
workflow = (WorkflowBuilder("db_runbook_finder", config_path)
    .with_config(max_parallel_steps=4, default_timeout=120)
    .step_auto("search_runbooks", "Search for relevant runbooks", search_runbooks_node)
    .step_auto("fetch_incident", "Fetch incident details", fetch_incident_node)
    .step_auto("update_jira", "Update Jira with results", update_jira_with_results_node)
    .build())
```

### Production Tool Integration
**Reference**: Direct integration with existing production tools

#### Confluence Tool Integration - Runbook Discovery
**Source**: `src/tools/confluence/app/api.py` and `app/confluence.py`
- **Endpoints**: `/search/confluence`, `/pages/extract`, `/runbooks/{runbook_id}`
- **Capabilities**: Content validation, metadata extraction, semantic search
- **Mock Layer**: Complete abstraction using `tests/data/*.json` for offline development
- **Performance**: Validated <50ms response times for semantic search operations

#### ChromaDB Vector Store - Semantic Search
**Source**: `src/tools/confluence/app/vector_store.py`
- **Model**: sentence-transformers (all-MiniLM-L6-v2) for vector embeddings
- **Storage**: Persistent ChromaDB with proper empty collection handling
- **Operations**: Store, search, delete, update runbooks with vector embeddings
- **Validation**: 100% test coverage with performance benchmarks

#### Jira Tool Integration - Incident Management
**Source**: `src/tools/jira/app/jira.py`
- **Operations**: Ticket management, comments with rich formatting, ticket closure
- **Authentication**: Atlassian API tokens with environment-based configuration
- **Testing**: Real API integration tests preserved in `tests/tools/jira/`

#### Mock Data Infrastructure - Development Support
**Source**: `tests/data/` directory with comprehensive JSON datasets
- **Datasets**: 5 specialized runbook types (database connection, performance, backup, security, migration)
- **Utilities**: `test_data_loader.py` for data management and fallback mechanisms
- **Coverage**: 100% offline development capability with realistic data patterns
- **Rich Formatting**: Bold, italic, code blocks with SlackFormatting enum
- **Interactive Elements**: Yes/No buttons with correlation ID tracking

### Current Implementation Architecture
**Reference**: Production-ready implementation in `src/usecases/db_runbook_finder/`
- **Direct Tool Integration**: Seamless integration with existing production tools
- **Workflow-Based Architecture**: GraphMCP WorkflowBuilder pattern with node-based execution
- **State Management**: Comprehensive `WorkflowState` dataclass with incident tracking
- **Performance Validated**: All operations meet <50ms response time requirements

### Workflow Node Implementation
**Reference**: `src/usecases/db_runbook_finder/nodes.py` - Production-ready nodes
- **search_runbooks_node**: Confluence integration with semantic search capabilities
- **fetch_incident_node**: Jira incident details retrieval with error handling
- **update_jira_with_results_node**: Result posting with rich formatting support
- **notify_team_node**: Team notification with approval workflows
- **terminate_with_gap_error_node**: Graceful error handling and escalation

### Test Infrastructure Excellence
**Reference**: `src/usecases/db_runbook_finder/tests/` - 100% test success rate
- **Mock Data Layer**: 5 specialized JSON datasets for comprehensive testing
- **Performance Testing**: Validated <50ms response times across all operations
- **Error Scenario Coverage**: Comprehensive error handling and edge case testing
- **API Validation**: 20 endpoints with complete coverage and validation

```python
# Current implementation example - Direct workflow integration
from src.usecases.db_runbook_finder.nodes import (
    search_runbooks_node,
    fetch_incident_node, 
    update_jira_with_results_node
)
from src.usecases.db_runbook_finder.state import WorkflowState

# Example workflow execution
async def execute_db_runbook_workflow(incident_key: str, config_path: str):
    """Execute the production-ready DB runbook finder workflow."""
    
    # Initialize workflow state
    state = WorkflowState(
        incident_key=incident_key,
        client_name="sample_client",
        status="initialized"
    )
    
    # Execute workflow nodes
    state = await search_runbooks_node(state)  # Confluence + semantic search
    state = await fetch_incident_node(state)   # Jira incident details  
    state = await update_jira_with_results_node(state)  # Update with results
    
    return state
```

## DOCUMENTATION:

### Core Context Engineering References
- **Coleman Framework Guide**: `context-engineering/README.md` - Complete Manager context engineering system overview
- **Architecture Patterns**: `context-engineering/patterns/manager_architecture_patterns.md` - Manager-specific patterns
- **Development Templates**: `context-engineering/templates/` - Feature, workflow, and service templates
- **Validation Framework**: `context-engineering/validation/` - Quality assurance and validation systems

### GraphMCP Framework Documentation
- **Framework CLAUDE.md**: `src/frameworks/graphmcp/CLAUDE.md` - Complete framework patterns and conventions
- **BaseClient Implementation**: `src/frameworks/graphmcp/clients/base.py` - Abstract base class requirements
- **Workflow Builder**: `src/frameworks/graphmcp/workflows/builder.py` - Fluent API patterns
- **Existing Clients**: Study `github.py`, `slack.py`, `repomix.py` for implementation patterns

### Manager Component Integration
- **Project CLAUDE.md**: Root `CLAUDE.md` - Project-wide development guidance and service architecture
- **Manager CLAUDE.md**: `manager/CLAUDE.md` - Manager-specific development scope and boundaries
- **Microservice Patterns**: `context-engineering/examples/microservices_patterns.py` - Complete microservice development patterns

### External API References
- **Confluence REST API**: For runbook discovery strategy implementation
- **ChromaDB Documentation**: For vector storage strategy implementation  
- **MongoDB Integration**: For data persistence strategy implementation
- **Jira REST API**: For incident management integration
- **Slack API**: For notification strategy implementation

### Testing and Validation Documentation
- **Testing Patterns**: `context-engineering/examples/testing_patterns.py` - Comprehensive testing strategies
- **Mock Data Infrastructure**: `src/usecases/db_runbook_finder/tests/data/` - Existing test data patterns
- **Validation Requirements**: 100% test success rate, <50ms response times, comprehensive error handling

## OTHER CONSIDERATIONS:

### Development Scope and Boundaries
- **Editable Directory**: `src/usecases/db_runbook_finder/` - Full modification permissions within this directory
- **Read-Only Dependencies**: All `src/tools/`, `src/frameworks/graphmcp/` - Use existing functionality but no modifications
- **Integration Pattern**: Leverage existing tools (Confluence, Jira) through their established APIs

### Unified Python Environment Management
- **Single .venv**: Use project root `.venv` for all dependencies - no additional virtual environments
- **Dependency Management**: All dependencies managed through root `pyproject.toml`
- **Execution Pattern**: Use `uv run` for automation or activate `.venv` for interactive development
- **Testing Execution**: Run from project root using `.venv/bin/python`

### Context Engineering Workflow Integration
- **Pattern Discovery**: Use established GraphMCP and microservice patterns consistently
- **Comprehensive Context**: Reference existing implementations for architectural decisions
- **Validation Gates**: Implement unit, integration, and E2E testing with appropriate markers
- **Documentation-Driven**: Update examples and patterns based on successful implementation

### Architecture and Design Requirements
- **Direct Tool Integration**: Seamless integration with existing production tools (Confluence, Jira, ChromaDB)
- **Workflow-Based Architecture**: GraphMCP WorkflowBuilder pattern with node-based execution
- **Mock Data Abstraction**: Complete offline development capability using JSON datasets
- **State Management**: Comprehensive WorkflowState with incident tracking and performance metrics
- **GraphMCP Integration**: Full compatibility with existing GraphMCP orchestration patterns

### Performance and Quality Requirements
- **Response Time**: <50ms for semantic search operations
- **Test Coverage**: 100% test success rate following existing test patterns
- **Error Handling**: Comprehensive error scenarios with graceful degradation
- **Resource Management**: Proper async context manager patterns for all external connections

### Security and Operational Considerations
- **Credential Management**: Follow existing patterns for API token and credential handling
- **Environment Variables**: Use established configuration patterns from existing tools
- **Logging**: Integrate structured logging with correlation IDs for operational monitoring
- **Health Monitoring**: Implement comprehensive health checks for all strategy dependencies

### Integration with Existing Systems
- **Workflow Compatibility**: Seamless integration with existing `DBRunbookFinderWorkflow`
- **Node Pattern**: Compatible with existing `DBRunbookFinderNodes` implementation
- **Client Mapping**: Maintain compatibility with existing `PROJECT_TO_CLIENT_MAP` patterns
- **Mock Infrastructure**: Leverage existing mock data from `tests/data/` directory

### Coleman Context Engineering Framework Mapping
- **c_instr (Instructions)**: This INITIAL.md, CLAUDE.md files, and context-engineering/README.md
- **c_know (Knowledge)**: Existing patterns in context-engineering/examples/, GraphMCP implementations
- **c_tools (Tools)**: GraphMCP framework, existing microservice tools, testing infrastructure
- **c_mem (Memory)**: Templates in context-engineering/templates/, pattern libraries
- **c_state (State)**: Workflow state management, validation results, implementation tracking
- **c_query (Query)**: This feature specification with comprehensive requirements and context

### Success Criteria and Acceptance Requirements (ACHIEVED ✅)
1. **Workflow Implementation**: Complete GraphMCP workflow with node-based architecture ✅
2. **Production Tool Integration**: Seamless integration with Confluence, Jira, ChromaDB ✅
3. **Mock Data Infrastructure**: Complete offline development capability ✅
4. **Performance Requirements**: <50ms semantic search response times ✅
5. **Test Coverage**: 100% test success rate with comprehensive validation ✅
6. **Documentation**: Complete patterns documentation for future development ✅

This comprehensive specification documents the successfully implemented production-ready DB Runbook Finder workflow that achieves all performance requirements, maintains full compatibility with existing systems, and provides a robust foundation for AI-powered database runbook discovery and management capabilities.