# Execute Manager PRP

Implement a Manager component feature using the PRP (Product Requirements Prompt) file with full context engineering methodology.

## PRP File: $ARGUMENTS

## Execution Process

1. **Load Manager PRP**
   - Read the specified PRP file from context-engineering/PRPs/active/
   - Understand all Manager component context and requirements
   - Review GraphMCP framework integration requirements
   - Check cross-component integration needs (Agent/UI compatibility)
   - Follow all instructions in the PRP and extend research if needed
   - Ensure you have all needed context to implement the Manager PRP fully
   - Do more web searches and Manager codebase exploration as needed

2. **ULTRATHINK for Manager**
   - Think hard before executing the plan for Manager component
   - Create a comprehensive Manager implementation plan addressing all requirements
   - Consider GraphMCP framework patterns and MCP client integration
   - Break down complex Manager tasks into smaller, manageable steps
   - Use the TodoWrite tool to create and track your Manager implementation plan
   - Identify Manager implementation patterns from existing code to follow
   - Reference Manager examples in context-engineering/examples/
   - Consider microservice patterns from src/tools/ for tool development
   - Plan for Manager API patterns, database integration, and AI features

3. **Execute the Manager Plan**
   - Execute the Manager PRP following established patterns
   - Implement all Manager code using FastAPI, async patterns, and type hints
   - Follow GraphMCP framework patterns for workflow development
   - Use Manager-specific patterns for database operations (MongoDB)
   - Implement proper error handling and logging using structured logging
   - Ensure cross-component compatibility with Agent and UI
   - Follow Manager microservice patterns for tool development

4. **Validate Manager Implementation**
   - Run Manager-specific validation commands:
     ```bash
     cd manager
     uv run ruff check . && uv run mypy .
     uv run pytest tests/unit/ -v
     uv run pytest tests/integration/ -v
     ```
   - For GraphMCP features:
     ```bash
     cd src/frameworks/graphmcp
     make test-all
     make lint
     ```
   - Run cross-component integration validation
   - Fix any Manager-specific failures
   - Re-run until all Manager validation passes

5. **Complete Manager Implementation**
   - Ensure all Manager checklist items are done
   - Run final Manager validation suite
   - Test Manager API endpoints if applicable
   - Verify GraphMCP workflow integration if applicable
   - Check Manager database operations and migrations
   - Verify Manager AI integration and LLM operations
   - Report Manager implementation completion status
   - Read the Manager PRP again to ensure complete implementation

6. **Reference Manager Context**
   - Always reference the Manager PRP and context files as needed
   - Use Manager INITIAL.md for comprehensive context
   - Reference Manager CLAUDE.md for development patterns
   - Check Manager examples in context-engineering/examples/
   - Consult GraphMCP framework documentation in src/frameworks/graphmcp/

## Manager-Specific Considerations

### GraphMCP Framework Integration
- Follow GraphMCP workflow builder patterns
- Use step_auto() method for workflow steps (preferred)
- Implement proper MCP client lifecycle management
- Use structured logging with workflow context

### Manager API Development
- Use FastAPI with proper type hints and Pydantic models
- Implement async/await patterns for all I/O operations
- Follow Manager authentication and authorization patterns
- Use proper error handling with standardized error responses

### Database Integration
- Use Manager DatabaseClient wrapper for MongoDB operations
- Follow context manager patterns for database connections
- Implement proper transaction handling where needed
- Use structured data models with validation

### AI Integration
- Follow Azure OpenAI integration patterns
- Use LangChain/LangGraph for complex AI workflows
- Implement proper prompt engineering and context management
- Use Langfuse for AI operation observability

### Microservice Development
- Follow Manager microservice patterns from src/tools/
- Use standardized FastAPI structure with own pyproject.toml
- Implement proper health checks and monitoring
- Follow containerization patterns with Docker

### Testing Requirements
- Implement comprehensive unit tests (80% coverage minimum)
- Add integration tests for Manager component interactions
- Include E2E tests for full workflow validation
- Add performance tests for Manager-specific operations

### Cross-Component Compatibility
- Maintain API contracts with Go Agent component
- Provide necessary endpoints for Streamlit UI component
- Ensure consistent data formats across components
- Test integration points with external components

Note: If Manager validation fails, use Manager-specific error patterns and debugging approaches to fix and retry. Always maintain Manager component consistency and follow established GraphMCP framework patterns.