# Execute Manager PRP

## PRP file: $ARGUMENTS

Execute a comprehensive PRP for the manager component with full validation and testing. This command implements features following manager-specific patterns and architecture.

## Pre-Execution Setup

1. **Environment Verification**
   ```bash
   cd manager
   # Verify development environment
   uv sync
   # Check infrastructure services
   docker-compose ps || echo "Start infrastructure: docker-compose up -d"
   ```

2. **Baseline Testing**
   ```bash
   cd manager
   # Run existing tests to ensure clean baseline
   uv run pytest tests/unit/ -v
   uv run pytest tests/integration/ -v
   ```

## Execution Process

1. **Read and Analyze PRP**
   - Understand feature requirements completely
   - Identify all implementation tasks
   - Note validation criteria and success metrics
   - Review manager-specific patterns to follow

2. **Implementation Following Manager Patterns**
   - Follow established patterns in `manager/src/`
   - Use existing database patterns from `src/database/`
   - Follow API patterns from `src/api.py` and modules
   - Integrate with Celery patterns if background processing needed
   - Use GraphMCP framework if workflow orchestration required

3. **Incremental Development with Validation**
   - Implement in small, testable increments
   - Run validation gates after each major step
   - Fix issues immediately before proceeding
   - Maintain manager component architecture integrity

## Validation Gates

### Code Quality
```bash
cd manager
# Linting and type checking
uv run ruff check --fix src/
uv run mypy src/
```

### Testing
```bash
cd manager
# Unit tests
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# Feature-specific tests
uv run pytest tests/ -k "test_new_feature" -v
```

### Service Integration
```bash
cd manager
# API health check
curl -f http://localhost:9123/health

# Database connectivity
python -c "from src.database.client import DatabaseClient; print('DB OK')"

# Redis connectivity (if using Celery)
python -c "import redis; r=redis.Redis(); r.ping(); print('Redis OK')"
```

### GraphMCP Framework (if applicable)
```bash
cd manager/src/frameworks/graphmcp
# Framework tests
make test-all

# Workflow validation
make demo
```

## Post-Implementation

1. **Documentation Updates**
   - Update CLAUDE.md if new patterns introduced
   - Add examples to relevant documentation
   - Update API documentation if endpoints added

2. **Integration Testing**
   - Test with other manager components
   - Verify Slack integration if applicable
   - Test Prometheus metrics if added

3. **Performance Validation**
   - Check API response times
   - Verify memory usage within limits
   - Test under expected load

## Success Criteria

Feature implementation is complete when:
- [ ] All PRP requirements implemented
- [ ] All validation gates pass
- [ ] Integration with existing manager components works
- [ ] Performance meets manager standards
- [ ] Documentation updated appropriately
- [ ] Tests provide adequate coverage

## Error Handling

If validation fails:
1. **Identify Root Cause**: Check logs, test output, error messages
2. **Fix Incrementally**: Address one issue at a time
3. **Re-validate**: Run relevant validation gates
4. **Document Fixes**: Update implementation notes

## Output

Provide summary including:
- Features implemented
- Validation results
- Integration points tested
- Performance metrics
- Next steps (if any)

Remember: The manager component is the core of the Ovora platform - ensure all implementations maintain high quality and integration standards.