# Create Manager PRP

## Feature file: $ARGUMENTS

Generate a complete PRP (Product Requirements Prompt) for Manager component feature implementation with thorough research and context engineering methodology. Ensure comprehensive context is passed to enable self-validation and iterative refinement within the Manager component ecosystem.

Read the Manager feature file first to understand what needs to be created, how Manager-specific examples help, GraphMCP framework integration requirements, and cross-component considerations.

The AI agent implementing the PRP only gets the context you include in the PRP. Assume the AI agent has access to the Manager codebase and same knowledge cutoff, so Manager-specific research findings must be included or referenced. The Agent has WebSearch capabilities for external documentation.

## Manager Research Process

1. **Manager Codebase Analysis**
   - Search for similar Manager features/patterns in the codebase
   - Check GraphMCP framework patterns in src/frameworks/graphmcp/
   - Review Manager API patterns in src/api.py and modules/
   - Examine Manager microservice patterns in src/tools/
   - Identify Manager database patterns in src/database/
   - Check Manager AI integration patterns in src/llm/
   - Note existing Manager conventions to follow
   - Check Manager test patterns for validation approach
   - Review Manager configuration patterns in src/config.py

2. **GraphMCP Framework Analysis**
   - Review GraphMCP workflow patterns and examples
   - Check MCP client implementations and patterns
   - Examine GraphMCP logging and error handling patterns
   - Review GraphMCP testing strategies and validation
   - Identify relevant workflow orchestration patterns

3. **Cross-Component Integration Analysis**
   - Check Agent API compatibility requirements
   - Review UI endpoint requirements and data models
   - Examine external service integration patterns
   - Verify Manager authentication and authorization patterns

4. **External Research**
   - Search for similar features/patterns online for Manager tech stack
   - FastAPI documentation and patterns (include specific URLs)
   - Azure OpenAI and LangChain implementation examples
   - MongoDB and async Python patterns
   - Celery and Redis task processing patterns
   - MCP server documentation and examples
   - Best practices and common pitfalls for Manager technologies

5. **Manager Context Clarification** (if needed)
   - Specific Manager patterns to mirror and where to find them?
   - GraphMCP integration requirements and examples?
   - Cross-component integration requirements?
   - Manager-specific validation and testing approaches?

## Manager PRP Generation

Using context-engineering/templates/prp_template.md as template:

### Critical Manager Context to Include

**Manager-Specific Documentation:**
- Manager INITIAL.md and CLAUDE.md references
- GraphMCP framework documentation URLs
- Manager API documentation and examples
- Manager microservice patterns from src/tools/
- Manager configuration and environment setup

**Manager Code Examples:**
- Real Manager code snippets from codebase
- GraphMCP workflow implementation examples
- Manager API endpoint patterns
- Manager database operation patterns
- Manager AI integration patterns

**Manager Gotchas:**
- Manager library quirks and version issues
- GraphMCP framework specific considerations
- Manager async/await patterns and pitfalls
- Manager database connection and transaction patterns
- Manager AI integration error handling

**Manager Patterns:**
- Existing Manager approaches to follow
- GraphMCP workflow orchestration patterns
- Manager microservice development patterns
- Manager testing and validation patterns
- Manager deployment and containerization patterns

### Manager Implementation Blueprint

**Architecture Context:**
- Manager component role in Ovora ecosystem
- GraphMCP framework integration approach
- Cross-component compatibility requirements
- Manager-specific performance and security considerations

**Implementation Strategy:**
- Start with pseudocode showing Manager approach
- Reference real Manager files for patterns
- Include Manager error handling strategy
- Define GraphMCP workflow integration if applicable
- Plan Manager database operations and AI integration
- List Manager tasks to be completed in implementation order

**Manager Dependencies:**
- Required Manager libraries and versions
- GraphMCP framework dependencies
- Manager environment variables and configuration
- External service integration requirements

### Manager Validation Gates (Must be Executable)

```bash
# Manager Code Quality
cd manager
uv run ruff check . && uv run mypy .

# Manager Unit Tests
uv run pytest tests/unit/ -v

# Manager Integration Tests
uv run pytest tests/integration/ -v

# GraphMCP Framework Tests (if applicable)
cd src/frameworks/graphmcp
make test-all
make lint

# Manager API Tests (if applicable)
cd manager
uv run pytest tests/api/ -v

# Manager Performance Tests (if applicable)
uv run pytest tests/performance/ -v

# Manager Security Tests (if applicable)
uv run pytest tests/security/ -v
```

### Manager-Specific Validation Requirements

**Functional Validation:**
- Manager API endpoint functionality
- GraphMCP workflow execution validation
- Manager database operations validation
- Manager AI integration validation
- Cross-component integration validation

**Quality Validation:**
- Manager code quality and type safety
- Manager test coverage (80% minimum)
- Manager performance criteria (< 500ms API response)
- Manager security validation
- Manager documentation completeness

**Integration Validation:**
- Agent component API compatibility
- UI component endpoint availability
- External service integration testing
- Manager deployment and containerization

*** CRITICAL MANAGER PRP DEVELOPMENT PROCESS ***

*** AFTER MANAGER RESEARCH AND CODEBASE EXPLORATION ***

*** ULTRATHINK ABOUT THE MANAGER PRP AND PLAN YOUR APPROACH ***

*** CONSIDER MANAGER ARCHITECTURE, GRAPHMCP INTEGRATION, AND CROSS-COMPONENT COMPATIBILITY ***

*** THEN START WRITING THE COMPREHENSIVE MANAGER PRP ***

## Output

Save as: `context-engineering/PRPs/active/{manager-feature-name}.md`

## Manager PRP Quality Checklist

- [ ] All necessary Manager context included
- [ ] GraphMCP framework integration considered
- [ ] Cross-component compatibility addressed
- [ ] Manager validation gates are executable
- [ ] References existing Manager patterns
- [ ] Clear Manager implementation path
- [ ] Manager error handling documented
- [ ] Manager testing strategy defined
- [ ] Manager performance considerations included
- [ ] Manager security requirements addressed
- [ ] Manager deployment considerations included

## Manager PRP Success Criteria

Score the Manager PRP on a scale of 1-10 for confidence level to succeed in one-pass implementation:

**Scoring Criteria:**
- 10: Complete Manager context, GraphMCP integration, executable validation
- 8-9: Comprehensive Manager context with minor gaps
- 6-7: Good Manager context but missing key integration details
- 4-5: Basic Manager context but significant gaps
- 1-3: Insufficient Manager context for successful implementation

**Target Score: 8-10** for Manager component features

Remember: The goal is one-pass Manager implementation success through comprehensive context engineering that leverages the full Manager component architecture, GraphMCP framework capabilities, and maintains perfect integration with the broader Ovora ecosystem.