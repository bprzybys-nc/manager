# GraphMCP Workflow Template

## Basic Information

**Workflow Name**: [Descriptive name for the workflow]
**Component**: Manager/GraphMCP Framework
**Purpose**: [Brief description of what this workflow accomplishes]
**Estimated Complexity**: [Simple/Medium/Complex]
**Dependencies**: [List any external services or components required]

## Business Context

### Problem Statement
[Describe the problem this workflow solves]

### Success Criteria
- [ ] [Specific, measurable outcome 1]
- [ ] [Specific, measurable outcome 2]
- [ ] [Specific, measurable outcome 3]

### Business Value
[Explain the business value and impact of this workflow]

## Technical Requirements

### Input Parameters
```python
@dataclass
class WorkflowInput:
    # Define input parameters with types
    param1: str
    param2: int
    optional_param: Optional[str] = None
```

### Expected Output
```python
@dataclass
class WorkflowOutput:
    # Define output structure with types
    result: bool
    data: Dict[str, Any]
    duration_seconds: float
```

### MCP Clients Required
- [ ] GitHub Client (`ovr_github`)
- [ ] Slack Client (`ovr_slack`) 
- [ ] Repomix Client (`ovr_repomix`)
- [ ] Filesystem Client (`ovr_filesystem`)
- [ ] Other: [Specify]

## Workflow Steps

### Step 1: [Step Name]
**Description**: [What this step does]
**MCP Client**: [Which client is used]
**Input**: [Step input requirements]
**Output**: [Step output]
**Error Handling**: [How errors are handled]

### Step 2: [Step Name]
**Description**: [What this step does]
**MCP Client**: [Which client is used]
**Input**: [Step input requirements]
**Output**: [Step output]
**Error Handling**: [How errors are handled]

[Continue for all steps...]

## Implementation Pattern

### Preferred Builder Pattern
```python
from frameworks.graphmcp.workflows.builder import WorkflowBuilder

workflow = (WorkflowBuilder("workflow_name", config_path)
    .with_config(
        max_parallel_steps=4,
        default_timeout=120,
        retry_attempts=3
    )
    .step_auto("step1", "Step 1 Description", step1_function)  # PREFERRED
    .step_auto("step2", "Step 2 Description", step2_function)
    .github_analyze_repo("analyze", repo_url)  # If using GitHub
    .slack_post("notify", channel_id, message)  # If using Slack
    .build())

result = await workflow.execute(input_params)
```

### Step Function Signatures
```python
async def step1_function(context: WorkflowContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 1 implementation.
    
    Args:
        context: Workflow context with clients and configuration
        input_data: Input data from previous steps or workflow input
        
    Returns:
        Dict containing step results
        
    Raises:
        MCPToolError: When MCP tool operations fail
        ValueError: When input validation fails
    """
    # Implementation here
    return {"success": True, "data": result_data}
```

## Error Handling Strategy

### Retry Strategy
- **Transient Failures**: Exponential backoff with max 3 retries
- **Network Failures**: Retry with jitter
- **Rate Limiting**: Respect rate limits and retry appropriately

### Graceful Degradation
- [Describe fallback behavior when services are unavailable]
- [Specify what can continue vs what must fail]

### Error Logging
```python
from frameworks.graphmcp.graphmcp_logging import get_logger

logger = get_logger(workflow_id=f"workflow_{name}")
logger.log_error("Step failed", step="step_name", exception=e)
```

## Performance Requirements

### Timing Constraints
- **Total Workflow Time**: [Maximum acceptable duration]
- **Step Timeouts**: [Individual step timeout requirements]
- **Resource Usage**: [Memory/CPU constraints]

### Scalability Considerations
- **Concurrent Executions**: [How many can run simultaneously]
- **Rate Limiting**: [External service rate limits to respect]
- **Caching**: [What can/should be cached]

## Testing Strategy

### Unit Tests
```python
# Test individual step functions
async def test_step1_function():
    context = MockWorkflowContext()
    input_data = {"param1": "test_value"}
    
    result = await step1_function(context, input_data)
    
    assert result["success"] is True
    assert "data" in result
```

### Integration Tests
```python
# Test workflow with mock clients
async def test_workflow_integration():
    workflow = build_workflow_with_mocks()
    input_params = WorkflowInput(param1="test")
    
    result = await workflow.execute(input_params)
    
    assert result.success is True
```

### End-to-End Tests
- [ ] Test with real MCP services (requires MCP server setup)
- [ ] Test error scenarios and recovery
- [ ] Test performance under load

## Monitoring and Observability

### Logging Requirements
- **Structured Logging**: Use GraphMCP logging framework
- **Correlation IDs**: Track requests across steps
- **Performance Metrics**: Log timing and resource usage

### Metrics to Track
- Workflow execution time
- Step success/failure rates
- Error types and frequencies
- Resource utilization

## Security Considerations

### Sensitive Data Handling
- [ ] No credentials in logs
- [ ] Secure parameter passing
- [ ] Proper secret management

### Access Control
- [ ] Required permissions documented
- [ ] Service account requirements
- [ ] Rate limiting considerations

## Configuration

### Environment Variables
```bash
# Required environment variables
VARIABLE_NAME=description_of_what_it_configures

# Optional environment variables
OPTIONAL_VAR=description_with_default_value
```

### MCP Server Configuration
```json
{
  "mcpServers": {
    "required_server": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-name"],
      "env": {
        "REQUIRED_TOKEN": "$TOKEN_ENV_VAR"
      }
    }
  }
}
```

## Validation Checklist

### Pre-Implementation
- [ ] All MCP clients identified and available
- [ ] Input/output schemas defined
- [ ] Error handling strategy documented
- [ ] Performance requirements specified

### Post-Implementation
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Error scenarios tested
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Documentation updated

## Deployment Notes

### Prerequisites
- MCP servers configured and accessible
- Required environment variables set
- Dependencies installed in virtual environment

### Rollout Strategy
- [ ] Deploy in development environment first
- [ ] Gradual rollout with monitoring
- [ ] Rollback plan documented

## Maintenance and Updates

### Regular Maintenance Tasks
- Monitor workflow performance metrics
- Update MCP client dependencies
- Review and update error handling

### Breaking Change Considerations
- Input/output schema changes
- MCP server API changes
- Performance requirement changes

## References

### Related Workflows
- [List similar workflows for reference]

### Documentation
- GraphMCP Framework: `src/frameworks/graphmcp/README.md`
- MCP Client Patterns: `src/frameworks/graphmcp/examples/`
- Workflow Builder: `src/frameworks/graphmcp/workflows/builder.py`

### Examples
- Database Decommissioning: `src/usecases/database_decommissioning/`
- Pattern Examples: `context-engineering/examples/graphmcp_workflow_patterns.py`