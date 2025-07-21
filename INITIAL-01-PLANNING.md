# INITIAL.md - DB Runbook Finder Prototype Planning

## Basic Information

**Feature Name**: DB Runbook Finder Prototype  
**Component**: Manager (GraphMCP Framework Use Case)  
**Priority**: High  
**Estimated Effort**: 2 weeks  
**Assignee**: AI Assistant with Context Engineering  

## Feature Description

### Goal
Create an AI-orchestrated workflow that automatically processes a Jira incident, performs semantic search against indexed Confluence runbooks, and determines the most relevant procedures. This prototype validates the feasibility of reducing incident response time from minutes to seconds.

### Business Justification
- **Problem**: MC-DBA team spends significant time manually searching for relevant runbooks during incident response
- **Impact**: Delays in incident resolution, potential for human error in finding correct procedures
- **Solution**: Automated runbook discovery using semantic search and AI orchestration
- **Value**: Reduce response time from minutes to seconds, improve accuracy of runbook selection

### User Stories

| # | Title | As a / I want / So that |
|---|-------|-------------------------|
| **P-1** | Basic Workflow Orchestration | **As a** MC-DBA engineer **I want** a LangGraph workflow that automatically processes incident tickets and finds relevant runbooks **So that** I receive structured runbook recommendations without manual searching |
| **P-2** | Slack Team Notifications | **As a** MC-DBA team member **I want** automated Slack alerts with runbook recommendations or gap notifications **So that** the team has rapid incident awareness |

## Functional Requirements

### Core Functionality
1. **Jira Ticket Processing**: Ingest Jira ticket key (e.g., "AGENT-6") and extract incident details
2. **Semantic Search**: Query indexed Confluence runbooks using vector search for relevant procedures
3. **Result Processing**: Return top 3 most relevant runbooks with structured recommendations
4. **Gap Handling**: Gracefully handle cases where no relevant runbooks are found
5. **Automated Updates**: Add structured comments to Jira tickets with findings
6. **Team Notifications**: Send Slack notifications summarizing workflow outcomes

### Success Criteria
- Workflow successfully processes Jira ticket AGENT-6
- Calls existing Confluence tool's vector search to find relevant runbooks
- If runbooks found: adds comment with top 3 recommendations to Jira ticket
- If no runbooks found: adds gap notification comment and terminates cleanly
- Posts outcome summary to #mc-dba-jira-notifications Slack channel
- Complete end-to-end process in under 30 seconds
- Validates against two real Jira tickets

## Technical Requirements

### Architecture Integration
- **Framework**: GraphMCP workflow orchestration (`src/frameworks/graphmcp`)
- **Existing Tools**: Leverage `src/tools/confluence`, `src/tools/jira`, Slack MCP
- **Workflow Engine**: LangGraph StateGraph with conditional routing
- **Data Storage**: ChromaDB vector database (existing Confluence tool integration)

### Data Model
```python
@dataclass
class WorkflowState:
    jira_key: str                    # Input ticket ID (e.g., "AGENT-6")
    incident_data: Dict[str, Any]    # Structured data from jira_get_issue
    runbooks: List[Dict[str, Any]]   # Runbook objects from vector search
    status: str                      # Final state: "SUCCESS" or "GAP_DETECTED"
```

### API Dependencies
1. **Jira Tool** (`src/tools/jira/`):
   - `GET /tickets/{ticket_id}` - Fetch incident details
   - `POST /tickets/{ticket_id}/comments` - Add result comments
2. **Confluence Tool** (`src/tools/confluence/`):
   - `POST /search/vector` - Semantic search functionality
   - Pre-indexed AAVA and MCDBA spaces required
3. **Slack MCP Tool**:
   - Message posting to #mc-dba-jira-notifications channel

## Implementation Context

### Existing Patterns to Follow
- **Use Case Structure**: Mirror `src/usecases/database_decommissioning/` organization
- **Workflow Builder**: Follow GraphMCP workflow patterns with `_build_workflow` method
- **MCP Integration**: Use existing MCP client patterns for tool orchestration
- **Error Handling**: Implement graceful degradation as shown in other use cases

### Similar Features for Reference
- **Database Decommissioning Workflow**: `src/usecases/unused_db_decommissioning/`
- **Confluence Vector Search**: `src/tools/confluence/app/vector_store.py` (726 lines)
- **Jira Management API**: `src/tools/jira/app/api.py`
- **GraphMCP Examples**: `src/frameworks/graphmcp/examples/`

### File Structure Target
```
src/usecases/db_runbook_finder/
├── __init__.py
├── nodes.py         # Workflow node implementations
├── state.py         # WorkflowState data class
├── workflow.py      # Main LangGraph StateGraph
└── tests/
    └── test_workflow.py  # Unit & integration tests
```

## Quality Requirements

### Performance
- End-to-end workflow completion: < 30 seconds
- Vector search response time: < 5 seconds
- Jira API operations: < 10 seconds total
- Slack notification: < 2 seconds

### Reliability
- Graceful handling of API failures
- Proper error logging and monitoring
- Workflow state persistence for debugging
- Retry logic for transient failures

### Testing Strategy
- **Unit Tests**: Mock MCP tool calls, test each node independently
- **Integration Tests**: Real API calls with pre-selected test tickets
- **Validation Cases**: Success scenario (runbooks found) and gap scenario (no runbooks)
- **Test Tickets**: AGENT-6 and one additional ticket for comprehensive testing

## Acceptance Criteria

### Primary Acceptance Criteria
1. ✅ Workflow ingests Jira ticket key "AGENT-6"
2. ✅ Vector search returns relevant runbooks from AAVA/MCDBA spaces
3. ✅ Top 3 runbook recommendations added as Jira comment (if found)
4. ✅ Gap notification comment added to Jira (if no runbooks found)
5. ✅ Slack notification sent to #mc-dba-jira-notifications with summary
6. ✅ Complete process execution under 30 seconds
7. ✅ Prototype validated against two real Jira tickets

### Technical Acceptance Criteria
1. ✅ Follows GraphMCP framework patterns and conventions
2. ✅ Integrates with existing Confluence and Jira tools
3. ✅ Implements proper error handling and logging
4. ✅ Includes comprehensive unit and integration tests
5. ✅ Code follows existing project style and structure
6. ✅ Documentation includes usage examples and troubleshooting

## Risk Assessment

### High-Risk Items
1. **Confluence Index Completeness**: AAVA/MCDBA spaces must be pre-indexed
2. **MCP Server Dependencies**: Requires jira, confluence, and slack MCP servers running
3. **API Rate Limits**: Jira/Confluence API throttling during testing

### Medium-Risk Items
1. **Vector Search Quality**: Semantic search relevance depends on indexed content quality
2. **Client Name Mapping**: PROJECT_TO_CLIENT_MAP logic needs validation

### Mitigation Strategies
- Pre-validate MCP server connectivity before implementation
- Create fallback error messages for API failures
- Implement configurable timeout and retry policies
- Test with known good/bad ticket examples

## Dependencies

### Technical Dependencies
- **Python Packages**: `langgraph`, existing GraphMCP framework
- **MCP Servers**: jira, confluence, slack (must be configured and running)
- **Infrastructure**: ChromaDB with pre-indexed runbook content

### Process Dependencies
- **Pre-requisite**: Index AAVA and MCDBA Confluence spaces using `/bulk/index` endpoint
- **Configuration**: MCP server configuration in `src/frameworks/graphmcp/mcp_config.json`
- **Credentials**: Jira, Confluence, and Slack API tokens in environment variables