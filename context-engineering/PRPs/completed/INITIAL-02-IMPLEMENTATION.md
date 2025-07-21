# INITIAL.md - DB Runbook Finder Implementation

## Basic Information

**Feature Name**: DB Runbook Finder Implementation  
**Component**: Manager (GraphMCP Framework Use Case)  
**Priority**: High  
**Estimated Effort**: 1 week  
**Assignee**: AI Assistant with Context Engineering  

## Feature Description

### Goal
Implement the DB Runbook Finder workflow as defined in INITIAL-01-PLANNING.md, creating a production-ready LangGraph workflow that processes Jira ticket AGENT-6 and finds relevant runbooks through semantic search.

### Implementation Scope
Create complete implementation of the db_runbook_finder use case including:
- Workflow orchestration using GraphMCP framework
- Node implementations for each workflow step
- State management and data flow
- Error handling and gap detection
- Comprehensive testing suite

## Functional Requirements

### Core Implementation Components
1. **WorkflowState Class**: Data structure managing workflow state and data flow
2. **Workflow Nodes**: Individual processing steps with specific responsibilities
3. **Conditional Routing**: Logic to handle success/gap scenarios
4. **MCP Integration**: Tool calls to existing Jira, Confluence, and Slack services
5. **Error Handling**: Graceful degradation and proper error reporting

### Workflow Node Specifications

#### `fetch_incident_node`
- **Input**: `state.jira_key` (e.g., "AGENT-6")
- **Process**: Call Jira MCP tool to fetch ticket details
- **Output**: Populate `state.incident_data` with summary, description, client name
- **Client Mapping**: Extract client name from project key using PROJECT_TO_CLIENT_MAP

#### `search_runbooks_node`
- **Input**: `state.incident_data`
- **Process**: Construct search query and call Confluence vector search
- **Output**: Populate `state.runbooks` with top 3 relevant results
- **Search Scope**: AAVA and MCDBA Confluence spaces

#### `update_jira_with_results_node`
- **Input**: `state.runbooks` (non-empty)
- **Process**: Format human-readable comment with runbook recommendations
- **Output**: Add structured comment to Jira ticket

#### `terminate_with_gap_error_node`
- **Input**: `state.runbooks` (empty)
- **Process**: Create gap notification comment
- **Output**: Add gap comment to Jira, set `state.status = "GAP_DETECTED"`

#### `notify_team_node`
- **Input**: `state.status`
- **Process**: Format appropriate Slack message based on outcome
- **Output**: Send notification to #mc-dba-jira-notifications channel

## Technical Requirements

### File Structure Implementation
```
src/usecases/db_runbook_finder/
├── __init__.py                  # Package initialization
├── state.py                     # WorkflowState dataclass definition
├── nodes.py                     # All workflow node implementations
├── workflow.py                  # DBRunbookFinderWorkflow class
└── tests/
    ├── __init__.py
    ├── test_nodes.py            # Unit tests for individual nodes
    ├── test_workflow.py         # Integration tests for full workflow
    └── conftest.py              # Test fixtures and configuration
```

### Implementation Details

#### `state.py` - WorkflowState Definition
```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class WorkflowState:
    """State management for DB Runbook Finder workflow."""
    jira_key: str
    incident_data: Dict[str, Any] = None
    runbooks: List[Dict[str, Any]] = None
    status: str = "PENDING"
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.incident_data is None:
            self.incident_data = {}
        if self.runbooks is None:
            self.runbooks = []
```

#### `workflow.py` - Main Workflow Class
```python
from frameworks.graphmcp.workflows.builder import WorkflowBuilder
from .state import WorkflowState
from .nodes import DBRunbookFinderNodes

class DBRunbookFinderWorkflow:
    """DB Runbook Finder workflow implementation using GraphMCP framework."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.nodes = DBRunbookFinderNodes()
    
    def _build_workflow(self):
        """Build LangGraph workflow with conditional routing."""
        workflow = (WorkflowBuilder("db_runbook_finder", self.config_path)
            .with_config(max_parallel_steps=1, default_timeout=120)
            .step_auto("fetch_incident", "Fetch Jira incident details", self.nodes.fetch_incident_node)
            .step_auto("search_runbooks", "Search for relevant runbooks", self.nodes.search_runbooks_node)
            .conditional_routing("runbook_search_router", self._runbook_search_router)
            .step_auto("update_jira_results", "Update Jira with results", self.nodes.update_jira_with_results_node)
            .step_auto("terminate_gap", "Handle gap scenario", self.nodes.terminate_with_gap_error_node)
            .step_auto("notify_team", "Send Slack notification", self.nodes.notify_team_node)
            .build())
        return workflow
    
    def _runbook_search_router(self, state: WorkflowState) -> str:
        """Route workflow based on runbook search results."""
        if state.runbooks and len(state.runbooks) > 0:
            return "update_jira_results"
        else:
            return "terminate_gap"
```

#### `nodes.py` - Node Implementations
```python
from typing import Dict, Any
from .state import WorkflowState

class DBRunbookFinderNodes:
    """Implementation of all workflow nodes for DB Runbook Finder."""
    
    # Project key to client name mapping
    PROJECT_TO_CLIENT_MAP = {
        "AGENT": "Agent System",
        "NESMCI": "Neste",
        "HEMCI": "Helvetia",
        "OVRMCI": "Ovora Internal",
        # Add more mappings as needed
    }
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
    
    async def fetch_incident_node(self, state: WorkflowState) -> WorkflowState:
        """Fetch incident details from Jira."""
        try:
            # Call Jira MCP tool to get ticket details
            response = await self.mcp_client.call_tool(
                "jira", 
                "get_ticket_details", 
                {"issueIdOrKey": state.jira_key}
            )
            
            # Extract relevant information
            fields = response.get("fields", {})
            project_key = fields.get("project", {}).get("key", "")
            
            state.incident_data = {
                "summary": fields.get("summary", ""),
                "description": fields.get("description", ""),
                "client": self.PROJECT_TO_CLIENT_MAP.get(project_key, "Unknown"),
                "project_key": project_key,
                "issue_type": fields.get("issuetype", {}).get("name", ""),
                "priority": fields.get("priority", {}).get("name", ""),
            }
            
            return state
            
        except Exception as e:
            state.error_message = f"Failed to fetch incident: {str(e)}"
            state.status = "ERROR"
            return state
    
    async def search_runbooks_node(self, state: WorkflowState) -> WorkflowState:
        """Search for relevant runbooks using vector search."""
        try:
            # Construct search query from incident data
            summary = state.incident_data.get("summary", "")
            description = state.incident_data.get("description", "")
            query = f"{summary} {description}".strip()
            
            if not query:
                state.runbooks = []
                return state
            
            # Call Confluence vector search
            response = await self.mcp_client.call_tool(
                "confluence",
                "vector_search",
                {
                    "query": query,
                    "space_keys": ["AAVA", "MCDBA"],  # Target spaces
                    "limit": 3
                }
            )
            
            # Store search results
            state.runbooks = response.get("results", [])
            
            return state
            
        except Exception as e:
            state.error_message = f"Failed to search runbooks: {str(e)}"
            state.status = "ERROR"
            return state
    
    async def update_jira_with_results_node(self, state: WorkflowState) -> WorkflowState:
        """Update Jira ticket with runbook recommendations."""
        try:
            # Format runbook recommendations
            comment_lines = [
                "🔍 **Automated Runbook Recommendations**",
                "",
                "Based on the incident description, here are the most relevant runbooks:",
                ""
            ]
            
            for i, runbook in enumerate(state.runbooks[:3], 1):
                title = runbook.get("title", "Unknown Title")
                url = runbook.get("url", "#")
                relevance = runbook.get("relevance_score", 0)
                
                comment_lines.extend([
                    f"**{i}. {title}**",
                    f"   📊 Relevance: {relevance:.1%}",
                    f"   🔗 Link: {url}",
                    ""
                ])
            
            comment_lines.extend([
                "---",
                "*This recommendation was generated automatically by the DB Runbook Finder.*"
            ])
            
            comment_text = "\n".join(comment_lines)
            
            # Add comment to Jira ticket
            await self.mcp_client.call_tool(
                "jira",
                "add_comment",
                {
                    "issueIdOrKey": state.jira_key,
                    "comment": comment_text
                }
            )
            
            state.status = "SUCCESS"
            return state
            
        except Exception as e:
            state.error_message = f"Failed to update Jira: {str(e)}"
            state.status = "ERROR"
            return state
    
    async def terminate_with_gap_error_node(self, state: WorkflowState) -> WorkflowState:
        """Handle gap scenario where no runbooks were found."""
        try:
            gap_comment = [
                "⚠️ **Runbook Gap Detected**",
                "",
                "No relevant runbooks were found for this incident.",
                "",
                "**Incident Details:**",
                f"- Summary: {state.incident_data.get('summary', 'N/A')}",
                f"- Client: {state.incident_data.get('client', 'Unknown')}",
                f"- Issue Type: {state.incident_data.get('issue_type', 'N/A')}",
                "",
                "**Next Steps:**",
                "1. Manual runbook search may be required",
                "2. Consider creating new runbook for this scenario",
                "3. Review and update indexed runbook content",
                "",
                "---",
                "*Gap detection performed automatically by DB Runbook Finder.*"
            ]
            
            comment_text = "\n".join(gap_comment)
            
            # Add gap comment to Jira
            await self.mcp_client.call_tool(
                "jira",
                "add_comment",
                {
                    "issueIdOrKey": state.jira_key,
                    "comment": comment_text
                }
            )
            
            state.status = "GAP_DETECTED"
            return state
            
        except Exception as e:
            state.error_message = f"Failed to handle gap: {str(e)}"
            state.status = "ERROR"
            return state
    
    async def notify_team_node(self, state: WorkflowState) -> WorkflowState:
        """Send Slack notification to team."""
        try:
            # Format message based on status
            if state.status == "SUCCESS":
                message = [
                    f"✅ **Runbook Recommendations Found** - {state.jira_key}",
                    "",
                    f"**Incident:** {state.incident_data.get('summary', 'N/A')}",
                    f"**Client:** {state.incident_data.get('client', 'Unknown')}",
                    f"**Runbooks Found:** {len(state.runbooks)}",
                    "",
                    f"🔗 View ticket: [Jira Link]"
                ]
            elif state.status == "GAP_DETECTED":
                message = [
                    f"⚠️ **Runbook Gap Detected** - {state.jira_key}",
                    "",
                    f"**Incident:** {state.incident_data.get('summary', 'N/A')}",
                    f"**Client:** {state.incident_data.get('client', 'Unknown')}",
                    "",
                    "No relevant runbooks found. Manual intervention required.",
                    "",
                    f"🔗 View ticket: [Jira Link]"
                ]
            else:
                message = [
                    f"❌ **Workflow Error** - {state.jira_key}",
                    "",
                    f"**Error:** {state.error_message}",
                    "",
                    f"🔗 View ticket: [Jira Link]"
                ]
            
            message_text = "\n".join(message)
            
            # Send Slack notification
            await self.mcp_client.call_tool(
                "slack",
                "send_message",
                {
                    "channel": "#mc-dba-jira-notifications",
                    "text": message_text
                }
            )
            
            return state
            
        except Exception as e:
            state.error_message = f"Failed to send notification: {str(e)}"
            state.status = "ERROR"
            return state
```

## Implementation Context

### Existing Patterns to Follow
- **GraphMCP Framework**: Use `WorkflowBuilder` with `step_auto()` method (PREFERRED)
- **Error Handling**: Follow graceful degradation patterns from existing use cases
- **MCP Integration**: Use async context manager patterns for tool calls
- **Logging**: Implement structured logging using `graphmcp_logging`

### Similar Features for Reference
- **Database Decommissioning**: `src/usecases/unused_db_decommissioning/workflow.py`
- **GraphMCP Examples**: `src/frameworks/graphmcp/examples/`
- **Tool Integration**: `src/tools/confluence/app/api.py` and `src/tools/jira/app/api.py`

### Configuration Requirements
- **MCP Config**: Ensure jira, confluence, and slack servers in `mcp_config.json`
- **Environment Variables**: Jira, Confluence, and Slack credentials in `.env`
- **Pre-requisite**: Index AAVA and MCDBA spaces using Confluence `/bulk/index`

## Quality Requirements

### Testing Strategy
```python
# test_workflow.py - Integration Test Example
class TestDBRunbookFinderWorkflow:
    
    @pytest.mark.integration
    async def test_full_workflow_success_case(self):
        """Test complete workflow with AGENT-6 ticket."""
        workflow = DBRunbookFinderWorkflow("mcp_config.json")
        initial_state = WorkflowState(jira_key="AGENT-6")
        
        result = await workflow.run(initial_state)
        
        assert result.status in ["SUCCESS", "GAP_DETECTED"]
        assert result.incident_data is not None
        # Additional assertions...
    
    @pytest.mark.unit
    def test_project_to_client_mapping(self):
        """Test client name extraction logic."""
        nodes = DBRunbookFinderNodes()
        assert nodes.PROJECT_TO_CLIENT_MAP["AGENT"] == "Agent System"
        # Additional mapping tests...
```

### Performance Requirements
- **Workflow Completion**: < 30 seconds end-to-end
- **API Response Times**: Jira < 10s, Confluence < 5s, Slack < 2s
- **Error Recovery**: Graceful handling of timeout and API failures

### Code Quality Standards
- **Type Hints**: Complete type annotations throughout
- **Documentation**: Google-style docstrings for all classes and methods
- **Error Handling**: Comprehensive exception handling with proper logging
- **Testing**: 90%+ code coverage with unit and integration tests

## Acceptance Criteria

### Implementation Completion Criteria
1. ✅ Complete file structure created in `src/usecases/db_runbook_finder/`
2. ✅ WorkflowState dataclass with all required fields
3. ✅ All five workflow nodes implemented with proper error handling
4. ✅ Conditional routing logic for success/gap scenarios
5. ✅ MCP tool integration for Jira, Confluence, and Slack
6. ✅ PROJECT_TO_CLIENT_MAP with AGENT mapping
7. ✅ Comprehensive test suite with unit and integration tests

### Functional Validation Criteria
1. ✅ Workflow processes AGENT-6 ticket successfully
2. ✅ Extracts incident data including client name mapping
3. ✅ Performs vector search against AAVA/MCDBA spaces
4. ✅ Handles both success and gap scenarios appropriately
5. ✅ Updates Jira with formatted comments
6. ✅ Sends appropriate Slack notifications
7. ✅ Completes full workflow under 30-second target

### Code Quality Validation
1. ✅ Follows GraphMCP framework patterns and conventions
2. ✅ Implements proper async/await patterns
3. ✅ Includes comprehensive error handling and logging
4. ✅ Passes all unit and integration tests
5. ✅ Meets code coverage requirements (90%+)
6. ✅ Follows existing project code style and structure

## Dependencies

### Technical Dependencies
- **GraphMCP Framework**: `src/frameworks/graphmcp/` (existing)
- **Existing Tools**: `src/tools/jira/`, `src/tools/confluence/` (existing)
- **Python Packages**: `langgraph`, `dataclasses`, `typing` (available)

### External Dependencies
- **MCP Servers**: jira, confluence, slack servers configured and running
- **API Credentials**: Valid tokens for Jira, Confluence, and Slack
- **Indexed Content**: AAVA and MCDBA Confluence spaces pre-indexed

### Process Dependencies
- **INITIAL-01-PLANNING.md**: Must be completed and approved
- **Branch**: Implementation on `feat/db_runbook_finder` branch
- **Testing Data**: AGENT-6 ticket available for testing