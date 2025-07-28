# DB Runbook Finder

AI-powered workflow for automatically processing Jira incidents and finding relevant Confluence runbooks through semantic search.

## Overview

The DB Runbook Finder is a production-ready GraphMCP workflow that reduces incident response time from minutes to seconds by automatically:

1. **Fetching Jira ticket details** with client name mapping
2. **Performing semantic search** across AAVA and MCDBA Confluence spaces  
3. **Updating Jira tickets** with top 3 runbook recommendations
4. **Sending Slack notifications** to the MC-DBA team
5. **Handling gaps gracefully** when no runbooks are found

## Architecture

### Components

- **`state.py`**: WorkflowState dataclass managing workflow data and status
- **`nodes.py`**: Five workflow nodes implementing business logic
- **`workflow.py`**: Main workflow orchestration using GraphMCP framework
- **`tests/`**: Comprehensive test suite with 90%+ coverage

### Workflow Nodes

1. **`fetch_incident_node`**: Retrieves Jira ticket details and maps project keys to client names
2. **`search_runbooks_node`**: Performs vector search against indexed Confluence runbooks
3. **`update_jira_with_results_node`**: Formats and adds runbook recommendations to Jira
4. **`terminate_with_gap_error_node`**: Handles cases where no runbooks are found
5. **`notify_team_node`**: Sends appropriate Slack notifications based on outcome

### Routing Logic

```python
def _runbook_search_router(state: WorkflowState) -> str:
    if state.is_error_state():
        return "notify_team"
    elif state.has_runbooks():
        return "update_jira_results"  # Success path
    else:
        return "terminate_gap"        # Gap path
```

## Usage

### Basic Usage

```python
from usecases.db_runbook_finder import DBRunbookFinderWorkflow

# Initialize workflow
workflow = DBRunbookFinderWorkflow()

# Process AGENT-6 ticket
result = await workflow.run("AGENT-6")

# Check results
if result.status == "SUCCESS":
    print(f"Found {len(result.runbooks)} runbooks")
elif result.status == "GAP_DETECTED":
    print("No relevant runbooks found")
```

### Advanced Usage

```python
# Custom configuration
workflow = DBRunbookFinderWorkflow(config_path="custom/mcp_config.json")

# Get workflow information
info = workflow.get_workflow_info()
print(f"Supported projects: {info['supported_projects']}")

# Validate configuration
validation = await workflow.validate_configuration()
print(f"Status: {validation['overall_status']}")
```

## Configuration

### MCP Server Configuration

Edit `src/frameworks/graphmcp/mcp_config.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "jira-mcp-server",
      "env": {"JIRA_API_TOKEN": "$JIRA_API_TOKEN"}
    },
    "confluence": {
      "command": "confluence-mcp-server", 
      "env": {"CONFLUENCE_API_TOKEN": "$CONFLUENCE_API_TOKEN"}
    },
    "slack": {
      "command": "slack-mcp-server",
      "env": {"SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN"}
    }
  }
}
```

### Environment Variables

Required variables in `.env`:

```bash
# Jira Integration
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@domain.com
JIRA_API_TOKEN=your_jira_api_token

# Confluence Integration  
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@domain.com
CONFLUENCE_API_TOKEN=your_confluence_api_token

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# GraphMCP Logging
GRAPHMCP_LOG_FILE=dbworkflow.log
GRAPHMCP_OUTPUT_FORMAT=dual
GRAPHMCP_CONSOLE_LEVEL=INFO
```

### Project to Client Mapping

Update `PROJECT_TO_CLIENT_MAP` in `nodes.py`:

```python
PROJECT_TO_CLIENT_MAP = {
    "AGENT": "Agent System",
    "NESMCI": "Neste", 
    "HEMCI": "Helvetia",
    "OVRMCI": "Ovora Internal",
    "OVR": "Ovora",
    # Add your project mappings here
}
```

## Testing

### Run All Tests

```bash
cd src/usecases/db_runbook_finder
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/ -m unit

# Integration tests (requires MCP servers)
pytest tests/ -m integration

# Performance tests
pytest tests/ -m performance

# Error handling tests
pytest tests/ -m error_handling
```

### Test Coverage

```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

## Performance

### Targets

- **End-to-end workflow**: < 30 seconds
- **Jira API operations**: < 10 seconds total
- **Vector search**: < 5 seconds
- **Slack notifications**: < 2 seconds

### Metrics

The workflow tracks detailed performance metrics:

```python
result = await workflow.run("AGENT-6")
print(f"Total duration: {result.get_total_duration():.2f}s")
print(f"Metrics: {result.performance_metrics}")
```

## Example Output

### Success Scenario

For ticket `AGENT-6` with database timeout issue:

**Jira Comment:**
```
🔍 **Automated Runbook Recommendations**

Based on the incident description, here are the most relevant runbooks:

**1. Database Connection Troubleshooting Guide**
   📊 Relevance: 92.0%
   📚 Space: MCDBA
   🔗 Link: https://confluence.example.com/display/MCDBA/DB+Connection+Troubleshooting

**2. Connection Pool Management Best Practices**
   📊 Relevance: 87.0%
   📚 Space: AAVA
   🔗 Link: https://confluence.example.com/display/AAVA/Connection+Pool+Management

**Additional Information:**
- Search performed against: AAVA, MCDBA spaces
- Client: Agent System
- Processing time: 4.23 seconds

---
*This recommendation was generated automatically by the DB Runbook Finder.*
```

**Slack Notification:**
```
✅ **Runbook Recommendations Found** - AGENT-6

**Incident:** Database connection timeout in production environment
**Client:** Agent System
**Runbooks Found:** 2
**Processing Time:** 4.23 seconds

**Top Recommendations:**
1. Database Connection Troubleshooting Guide (92.0% relevance)
2. Connection Pool Management Best Practices (87.0% relevance)

🔗 View ticket: [Jira Link](#AGENT-6)
```

### Gap Scenario

For novel issues with no relevant runbooks:

**Jira Comment:**
```
⚠️ **Runbook Gap Detected**

No relevant runbooks were found for this incident in the indexed knowledge base.

**Recommended Next Steps:**
1. Perform manual search in AAVA and MCDBA Confluence spaces
2. Consult with senior team members for similar incidents
3. Consider creating new runbook for this scenario

---
*Gap detection performed automatically by DB Runbook Finder.*
```

## Integration

### API Integration

```python
from fastapi import APIRouter
from usecases.db_runbook_finder import DBRunbookFinderWorkflow

router = APIRouter()

@router.post("/runbook-finder/{jira_key}")
async def find_runbooks(jira_key: str):
    workflow = DBRunbookFinderWorkflow()
    result = await workflow.run(jira_key)
    return {
        "status": result.status,
        "client": result.get_client_name(),
        "runbooks_found": len(result.runbooks),
        "duration": result.get_total_duration()
    }
```

### CLI Integration

```bash
# Run workflow from command line
cd src/usecases/db_runbook_finder
python -c "
import asyncio
from workflow import DBRunbookFinderWorkflow

async def main():
    workflow = DBRunbookFinderWorkflow()
    result = await workflow.run('AGENT-6')
    print(f'Status: {result.status}')
    print(f'Client: {result.get_client_name()}')
    print(f'Runbooks: {len(result.runbooks)}')

asyncio.run(main())
"
```

## Prerequisites

### Confluence Indexing

Before using the workflow, ensure AAVA and MCDBA spaces are indexed:

```bash
# Index Confluence spaces for vector search
curl -X POST http://localhost:8000/confluence/bulk/index \
  -H "Content-Type: application/json" \
  -d '{"space_keys": ["AAVA", "MCDBA"]}'
```

### MCP Server Setup

1. **Install MCP servers**:
   ```bash
   npm install -g @modelcontextprotocol/server-jira
   npm install -g @modelcontextprotocol/server-confluence
   npm install -g @modelcontextprotocol/server-slack
   ```

2. **Configure credentials** in environment variables

3. **Test connectivity**:
   ```bash
   cd src/frameworks/graphmcp
   python -c "from clients.github import GitHubMCPClient; print('MCP OK')"
   ```

## Troubleshooting

### Common Issues

1. **Import errors**: Check Python path and GraphMCP framework installation
2. **MCP connection failures**: Verify MCP server configuration and credentials  
3. **Empty search results**: Ensure Confluence spaces are properly indexed
4. **Performance issues**: Check network connectivity and API rate limits

### Debug Mode

Enable debug logging:

```bash
export GRAPHMCP_CONSOLE_LEVEL=DEBUG
export GRAPHMCP_FILE_LEVEL=DEBUG
```

### Log Analysis

```bash
# View workflow logs
tail -f dbworkflow.log | grep "db_runbook_finder"

# Search for errors
grep ERROR dbworkflow.log | grep "db_runbook_finder"
```

## Contributing

1. **Follow established patterns** from GraphMCP framework
2. **Add comprehensive tests** for new functionality
3. **Update documentation** for any changes
4. **Use type hints** throughout
5. **Follow async/await patterns**

### Adding New Project Mappings

1. Update `PROJECT_TO_CLIENT_MAP` in `nodes.py`
2. Add test cases in `tests/test_nodes.py`
3. Update documentation examples

### Extending Functionality

1. Add new nodes in `nodes.py`
2. Update workflow routing in `workflow.py`
3. Add corresponding tests
4. Update this README

## License

This implementation is part of the SysAIdmin (Ovora) project.