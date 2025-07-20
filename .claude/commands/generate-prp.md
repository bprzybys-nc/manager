# Create Manager PRP

## Feature file: $ARGUMENTS

Generate a complete PRP (Product Requirements Prompt) for manager component feature implementation with thorough research. Ensure context is passed to the AI agent to enable self-validation and iterative refinement. Read the feature file first to understand what needs to be created, how the examples provided help, and any other considerations.

The AI agent only gets the context you are appending to the PRP and training data. Assume the AI agent has access to the manager codebase and the same knowledge cutoff as you, so it's important that your research findings are included or referenced in the PRP. The Agent has WebSearch capabilities, so pass URLs to documentation and examples.

## Research Process

1. **Manager Codebase Analysis**
   - Search for similar features/patterns in `manager/src/`
   - Identify files to reference in PRP (API routes, database models, tools)
   - Note existing conventions to follow (FastAPI patterns, database patterns)
   - Check test patterns for validation approach
   - Review GraphMCP framework usage patterns

2. **External Research**
   - Search for similar features/patterns online
   - Library documentation (include specific URLs)
   - Implementation examples (GitHub/StackOverflow/blogs)
   - Best practices and common pitfalls
   - Python/FastAPI specific patterns

3. **Manager Component Context**
   - Review manager-specific architecture patterns
   - Check microservices tool patterns in `src/tools/`
   - Understand AI integration patterns in `src/llm/`
   - Review Celery task patterns for background processing
   - Consider Slack integration requirements

4. **User Clarification** (if needed)
   - Specific patterns to mirror and where to find them?
   - Integration requirements with other manager components?
   - GraphMCP workflow integration needs?

## PRP Generation

Using comprehensive context engineering principles:

### Critical Context to Include and pass to the AI agent as part of the PRP
- **Documentation**: URLs with specific sections
- **Code Examples**: Real snippets from manager codebase
- **Manager Patterns**: Existing implementations to follow
- **Gotchas**: Library quirks, version issues, manager-specific considerations
- **Integration Points**: Database, API, Celery, Slack, GraphMCP patterns

### Implementation Blueprint
- Start with pseudocode showing approach
- Reference real files for patterns in manager/src/
- Include error handling strategy following manager conventions
- Consider microservices architecture implications
- List tasks to be completed to fulfill the PRP in order they should be completed

### Manager-Specific Validation Gates (Must be Executable)
```bash
# Syntax/Style
cd manager && uv run ruff check --fix && uv run mypy src/

# Unit Tests
cd manager && uv run pytest tests/unit/ -v

# Integration Tests
cd manager && uv run pytest tests/integration/ -v

# API Tests (if applicable)
cd manager && uv run pytest tests/api/ -v

# Service Health Check
cd manager && curl -f http://localhost:9123/health || echo "Service not running"
```

### GraphMCP Integration Validation (if applicable)
```bash
# GraphMCP Framework Tests
cd manager/src/frameworks/graphmcp && make test-all

# Workflow Validation
cd manager/src/frameworks/graphmcp && make demo
```

*** CRITICAL AFTER YOU ARE DONE RESEARCHING AND EXPLORING THE MANAGER CODEBASE ***

*** ULTRATHINK ABOUT THE PRP AND PLAN YOUR APPROACH ***

*** THEN START WRITING THE COMPREHENSIVE PRP ***

## Output
Save as: `context-engineering/PRPs/active/{feature-name}.md`

## Quality Checklist
- [ ] All necessary manager context included
- [ ] Validation gates are executable by AI
- [ ] References existing manager patterns
- [ ] Clear implementation path for manager component
- [ ] Error handling documented
- [ ] Integration points with other manager components considered
- [ ] GraphMCP framework integration considered (if applicable)
- [ ] Microservices architecture implications addressed

## PRP Success Criteria

Score the PRP on a scale of 1-10 for confidence level to succeed in one-pass implementation:

**Scoring Criteria:**
- 10: Complete context, executable validation gates, comprehensive research
- 8-9: Thorough context with minor gaps
- 6-7: Good context but missing key details
- 4-5: Basic context but significant gaps
- 1-3: Insufficient context for successful implementation

**Target Score: 8-10** for manager component features

Remember: The goal is one-pass implementation success through comprehensive context engineering.