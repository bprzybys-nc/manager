# INITIAL.md - RunbookRepositoryMCP Server

## FEATURE:
Create a comprehensive RunbookRepositoryMCP server that implements a quadruple strategy pattern architecture within the `src/usecases/db_runbook_finder/` directory. This MCP server will serve as the single source of truth for all node and helper functionality in runbook-related workflows, abstracting external dependencies through four Protocol-based strategy interfaces: RunbookDiscoveryStrategy, VectorStorageStrategy, DataPersistenceStrategy, and NotificationStrategy. The server will follow GraphMCP BaseClient patterns while using Python's `typing.Protocol` for structural subtyping, enabling flexible implementation swapping and retroactive compatibility with existing tools (Confluence, Jira, Slack Communication).

## EXAMPLES:

### GraphMCP BaseClient Pattern Integration
**Reference**: `src/frameworks/graphmcp/clients/base.py`
- **SERVER_NAME Class Attribute**: Each MCP client must define `SERVER_NAME = "runbook_repository"` for proper identification
- **Async Context Manager Support**: Full `async with` support using `__aenter__` and `__aexit__` methods
- **Error Handling Hierarchy**: Custom exceptions (`MCPConnectionError`, `MCPToolError`) with structured error messages
- **Tool Calling Pattern**: Use `call_tool_with_retry()` method with exponential backoff for reliability

```python
# Example from BaseClient pattern
class RunbookRepositoryMCPClient(BaseMCPClient):
    SERVER_NAME = "runbook_repository"  # Required class attribute
    
    async def list_available_tools(self) -> list[str]:
        # Implementation following base pattern
        
    async def health_check(self) -> bool:
        # Implementation following base pattern
```

### Strategy Implementation with Existing Tools
**Reference**: Detailed analysis in `MCP_FUNCTIONALITY_REPORT.md`

#### RunbookDiscoveryStrategy - Confluence Tool Integration
**Source**: `src/tools/confluence/app/api.py` and `app/confluence.py`
- **Real Operations**: `/search/confluence`, `/pages/extract`, `/runbooks/{runbook_id}`
- **Working Operations**: Content validation and metadata extraction
- **Mock Fallback**: Test data from `tests/data/*.json` for offline development

#### VectorStorageStrategy - ChromaDB Integration  
**Source**: `src/tools/confluence/app/vector_store.py`
- **Real Operations**: Semantic search with sentence-transformers (all-MiniLM-L6-v2)
- **Performance**: <50ms response times, persistent ChromaDB storage
- **Vector Operations**: Store, search, delete, update runbooks with embeddings

#### DataPersistenceStrategy - Jira + Mock Hybrid
**Source**: `src/tools/jira/app/jira.py` + mock tracking patterns
- **Real Operations**: Jira ticket management, comments, ticket closure
- **Mock Operations**: Runbook usage tracking and effectiveness metrics
- **Test Data**: Leverage existing patterns from job management systems

#### NotificationStrategy - Slack Communication Tool
**Source**: `src/tools/communication/app/slack.py`
- **Real Operations**: Thread creation, messaging, interactive approvals
- **Rich Formatting**: Bold, italic, code blocks with SlackFormatting enum
- **Interactive Elements**: Yes/No buttons with correlation ID tracking

### Manager Microservice Patterns
**Reference**: `context-engineering/examples/microservices_patterns.py`
- **FastAPI Application Factory**: Use `create_microservice_app()` for consistent service setup
- **Health Endpoint Standards**: Implement `/health`, `/health/ready`, `/health/live` following established patterns
- **Error Handler Registration**: Use `add_error_handlers()` for consistent exception management
- **Dependency Injection**: Follow `create_dependency_provider()` pattern for external service integration

### Existing DB Runbook Finder Implementation
**Reference**: `src/usecases/db_runbook_finder/workflow.py`, `src/usecases/db_runbook_finder/nodes.py`
- **Workflow State Management**: Use `WorkflowState` class with status tracking and error handling
- **Node Implementation Pattern**: Follow `DBRunbookFinderNodes` structure for workflow operations
- **GraphMCP Integration**: Use `WorkflowBuilder` pattern with `step_auto()` method preference
- **Structured Logging**: Integrate `graphmcp_logging` with correlation IDs and comprehensive error tracking

### Strategy Pattern Architecture with Python Protocols
**Reference**: Context engineering principles, existing GraphMCP implementations, and Python typing best practices
- **Protocol-Based Interfaces**: Use `typing.Protocol` for structural subtyping instead of ABC for maximum flexibility
- **Four Strategy Interfaces**: RunbookDiscovery, VectorStorage, DataPersistence, Notification strategies
- **Structural Subtyping**: Enable duck-typing compatibility without explicit inheritance requirements
- **Implementation Swapping**: Design for future replacement without breaking dependent workflows
- **Retroactive Compatibility**: Existing tools (Confluence, Jira, Slack) can implement protocols without modification
- **Tool Integration**: Direct HTTP client integration with existing microservice endpoints

```python
# Protocol-based interface example
from typing import Protocol, List, Dict, Any, Optional

class RunbookDiscoveryStrategy(Protocol):
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        """Discover runbooks in specified spaces."""
        ...
    
    async def get_runbook_content(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific runbook content."""
        ...
    
    async def validate_runbook_content(self, page: Dict[str, Any]) -> bool:
        """Validate runbook content structure."""
        ...
    
    async def extract_runbook_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from runbook page."""
        ...

# Existing tool classes can implement protocols without inheritance
class ConfluenceRunbookStrategy:  # No explicit inheritance needed
    """Implements RunbookDiscoveryStrategy via structural subtyping."""
    
    def __init__(self, confluence_client):
        self.client = confluence_client
    
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        # Implementation using existing Confluence tool
        return await self.client.search_spaces(spaces)
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
- **Quadruple Strategy Pattern**: Implement four abstraction interfaces using Python Protocol typing for structural subtyping:
  1. `RunbookDiscoveryStrategy` - Abstract runbook discovery (Confluence, mock, file-based)
  2. `VectorStorageStrategy` - Abstract vector operations (ChromaDB, alternatives)  
  3. `DataPersistenceStrategy` - Abstract data persistence (MongoDB, Jira, alternatives)
  4. `NotificationStrategy` - Abstract notifications (Slack, email, alternatives)
- **Python Interface Design**: Use `typing.Protocol` for duck-typing interfaces rather than ABC, enabling structural subtyping and retroactive implementation compatibility
- **Future-Proof Design**: Enable strategy swapping without breaking dependent workflows through Protocol-based interfaces
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

### Success Criteria and Acceptance Requirements
1. **MCP Server Implementation**: Complete server following GraphMCP BaseClient pattern with SERVER_NAME
2. **Triple Strategy Architecture**: Three interfaces implemented with mock and production strategies
3. **Workflow Integration**: Seamless replacement of current nodes with MCP server calls
4. **Test Coverage**: 100% success rate with comprehensive unit, integration, and E2E tests
5. **Performance Validation**: <50ms response times for core operations
6. **Documentation**: Complete patterns documentation for future development
7. **Context Engineering Compliance**: Full integration with established context engineering principles

This comprehensive context provides the foundation for implementing a production-ready RunbookRepositoryMCP server that follows all established patterns, maintains full compatibility with existing systems, and provides the abstraction needed for future evolution of the runbook discovery and management capabilities.