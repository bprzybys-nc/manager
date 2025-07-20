# Execute PRP

Implement a feature using the PRP file.

## PRP File: $ARGUMENTS

## Execution Process

1. **Load PRP**
   - Read the specified PRP file from context-engineering/PRPs/active/
   - Understand all context and requirements
   - Follow all instructions in the PRP and extend research if needed
   - Ensure you have all needed context to implement the PRP fully
   - Do more web searches and codebase exploration as needed

2. **ULTRATHINK**
   - Think hard before executing the plan
   - Create a comprehensive implementation plan addressing all requirements
   - Break down complex tasks into smaller, manageable steps
   - Use the TodoWrite tool to create and track your implementation plan
   - Identify implementation patterns from existing code to follow

3. **Execute the plan**
   - Execute the PRP following established Manager patterns
   - Implement all code using Manager conventions (FastAPI, async patterns, type hints)
   - Follow GraphMCP framework patterns if workflow development needed
   - Use Manager-specific patterns for database operations and AI integration

4. **Validate**
   - Run each validation command from the PRP
   - For Manager features, typically:
     ```bash
     cd manager
     uv run ruff check --fix src/ && uv run mypy src/
     uv run pytest tests/unit/ -v
     uv run pytest tests/integration/ -v
     ```
   - Fix any failures
   - Re-run until all pass

5. **Complete**
   - Ensure all checklist items are done
   - Run final validation suite
   - Report completion status
   - Read the PRP again to ensure complete implementation

6. **Reference the PRP**
   - You can always reference the PRP again if needed

Note: If validation fails, use error patterns in PRP to fix and retry. For Manager features, maintain component consistency and follow established patterns.