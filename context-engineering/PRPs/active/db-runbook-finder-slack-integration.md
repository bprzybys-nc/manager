# DB Runbook Finder Slack Integration - Product Requirements Prompt

## Executive Summary

Implement real Slack API integration for the DB Runbook Finder workflow, replacing current mock logging with production-ready GraphMCP SlackMCPClient integration. Additionally, enhance the workflow with ChromaDB-based runbook search and rich progress formatting throughout the entire workflow execution.

**Target Implementation**: Lines 427-431 in `src/usecases/db_runbook_finder/nodes.py`  
**Scope**: Real Slack notifications, workflow logic improvements, progress display enhancements  
**Architecture**: GraphMCP framework integration with existing Manager component patterns

## Context Engineering Research

### Current Implementation Analysis

**File Structure:**
```
src/usecases/db_runbook_finder/
├── nodes.py              # Main workflow nodes (target: lines 427-431)
├── workflow.py           # Workflow orchestration
├── state.py              # WorkflowState dataclass
└── scripts/              # Rich formatting reference patterns
    ├── search_runbooks.py    # Progress display patterns ✅
    ├── list_runbooks.py      # Rich formatting examples ✅
    └── README.md            # Usage documentation
```

**Current Mock Implementation** (lines 427-431):
```python
# Direct tool integration point (future enhancement)
# TODO: Implement direct Slack tool integration when available
# if self.use_real_tools and self.slack_configured:
#     from src.tools.communication.slack import SlackClient  # ❌ Wrong import
#     slack_client = SlackClient()
#     await slack_client.send_message("#mc-dba-jira-notifications", message_text)

# Mock notification (current fallback)
self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
self.logger.log_debug(f"Notification content preview: {message_text[:100]}...")
```

### Production Slack Integration Patterns

**GraphMCP SlackMCPClient** (`src/frameworks/graphmcp/clients/slack.py`):
```python
class SlackMCPClient(BaseMCPClient):
    SERVER_NAME = "ovr_slack"
    
    async def post_message(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
        # MCP tool call to Slack server
        # Returns: {"success": bool, "error": str, "message_ts": str}
```

**MCP Configuration** (`src/frameworks/graphmcp/clients/mcp_config.json`):
```json
{
  "ovr_slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN"
    }
  }
}
```

**Production Usage Pattern** (from `src/usecases/db_incident_assistant/`):
- HTTP endpoint integration via communication service
- Correlation ID tracking for interactive workflows
- Graceful degradation when services unavailable

### ChromaDB Integration Patterns

**Vector Store Implementation** (`tools/confluence/app/vector_store.py`):
```python
class VectorStore:
    def __init__(self, collection_name: str = 'default'):
        self._collection = self._client.get_collection(name=collection_name)
    
    def search_runbooks(self, query: str, n_results: int = 5) -> List[RunbookSearchResult]:
        # Critical: Handle empty collection
        collection_count = self._collection.count()
        if collection_count == 0:
            return []  # Prevents ChromaDB "Number of requested results 0" error
        
        # Runbook-level aggregation with weighted scoring
        aggregate_score = (0.7 * max_score) + (0.3 * avg_score)
```

**Target Collection**: `mcdb-runbooks` (pre-populated with discovered runbooks)

### Rich Progress Display Patterns

**Reference Implementation** (`src/usecases/db_runbook_finder/scripts/search_runbooks.py`):
```python
# Step headers with emojis and separators
print(f'🔍 Searching: "{query}"')
print(f'📊 Collection: mcdb-runbooks ({count} chunks)')
print('='*60)

# Results formatting with relevance indicators
for i, result in enumerate(results, 1):
    client = "🏢 Helvetia" if "helvetia" in result.metadata.tags else "🏢 Neste"
    
    # Relevance scoring with emojis
    if score >= 0.8:
        relevance = "🎯 Very Relevant"
    elif score >= 0.6:
        relevance = "✅ Relevant"  
    elif score >= 0.4:
        relevance = "⚠️ Somewhat Relevant"
    else:
        relevance = "❌ Low Relevance"
    
    print(f'{i}. 📖 {result.metadata.title}')
    print(f'   {client} | {relevance} ({score:.3f})')

# Completion indicators
print('='*60)
print(f'✅ Search completed - {len(results)} results')
```

## Technical Specifications

### Environment Configuration

**Required Environment Variables** (`.env`):
```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-***             # Bot token for API operations
SLACK_APP_TOKEN=xapp-***             # App token for Socket Mode (if needed)
SLACK_CHANNEL=C066PQYUYR4            # Target channel ID for #mc-dba-jira-notifications

# Confluence/ChromaDB (existing)
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_USERNAME=service@company.com
CONFLUENCE_API_TOKEN=***

# Database (existing)
MONGO_DB_URI=mongodb://localhost:27017
```

### Architecture Integration Points

**1. Constructor Modification** (`DBRunbookFinderNodes`):
```python
class DBRunbookFinderNodes:
    def __init__(self, config_path: str, use_real_tools: bool = False):
        self.config_path = config_path  # Path to MCP configuration
        self.use_real_tools = use_real_tools
        self.slack_configured = self._check_tool_configured("SLACK")
        # ... existing initialization
```

**2. MCP Config Path**: `"src/frameworks/graphmcp/clients/mcp_config.json"`

**3. Channel Specifications**:
- **Channel Name**: "#mc-dba-jira-notifications"
- **Channel ID**: "C066PQYUYR4"
- **Target Audience**: MC-DBA team for workflow notifications

### External Resources & Documentation

**Model Context Protocol (MCP) - 2024**:
- **Official Documentation**: https://modelcontextprotocol.io/
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Slack MCP Integration**: https://www.getguru.com/reference/slack-mcp
- **Anthropic MCP Guide**: https://www.philschmid.de/mcp-introduction

**Rich Console Library**:
- **Official Docs**: https://rich.readthedocs.io/en/stable/
- **Progress Display**: https://rich.readthedocs.io/en/stable/progress.html
- **Real Python Guide**: https://realpython.com/python-rich-package/
- **Emoji Integration**: Full Unicode emoji support via `:emoji_name:` syntax

**ChromaDB Vector Database**:
- **Real Python Guide**: https://realpython.com/chromadb-vector-database/
- **Best Practices**: https://www.analyticsvidhya.com/blog/2023/07/guide-to-chroma-db-a-vector-store-for-your-generative-ai-llms/
- **Empty Collection Handling**: Known issue documented in GitHub issues

**Slack API Documentation**:
- **Web API**: https://api.slack.com/web
- **Python SDK**: https://github.com/slackapi/python-slack-sdk
- **MCP Integration Examples**: https://github.com/seratch/slack-mcp-bot-integration

## Implementation Blueprint

### Phase 1: Constructor and Configuration Setup

**Target**: Add config_path parameter and update initialization

```python
# In src/usecases/db_runbook_finder/nodes.py
class DBRunbookFinderNodes:
    def __init__(self, config_path: str, use_real_tools: bool = False):
        self.config_path = config_path
        self.use_real_tools = use_real_tools
        self.slack_configured = self._check_tool_configured("SLACK")
        
        # Initialize vector store for ChromaDB integration
        self.vector_store = VectorStore(collection_name='mcdb-runbooks')
        
        # Initialize logger with rich formatting capabilities
        self.logger = get_logger(workflow_id="db_runbook_finder")
```

**Integration Point**: Workflow initialization must pass config_path:
```python
# In workflow.py or caller
config_path = "src/frameworks/graphmcp/clients/mcp_config.json"
nodes = DBRunbookFinderNodes(config_path=config_path, use_real_tools=True)
```

### Phase 2: ChromaDB Integration Enhancement

**Target**: Replace Confluence API calls with direct ChromaDB search

```python
async def search_runbooks_node(self, state: WorkflowState) -> WorkflowState:
    """Enhanced runbook search with rich progress display."""
    
    # Progress display - Step header
    print(f'🔍 Searching runbooks for: "{state.search_query}"')
    
    # Collection validation with progress
    count = self.vector_store._collection.count()
    print(f'📊 Collection: mcdb-runbooks ({count} chunks)')
    
    if count == 0:
        print("❌ No runbooks found in collection.")
        state.status = "GAP_DETECTED"
        state.error_details = "ChromaDB collection is empty"
        return state
    
    print('='*60)
    
    try:
        # Perform semantic search with progress indicator
        print("🔄 Performing semantic search...")
        results = self.vector_store.search_runbooks(state.search_query, n_results=5)
        
        if not results:
            print("🤷 No relevant runbooks found for query.")
            state.status = "GAP_DETECTED"
            return state
        
        # Rich results formatting
        print(f'📋 Found {len(results)} relevant results:')
        print()
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            # Client identification
            client = "🏢 Helvetia" if "helvetia" in result.metadata.tags else "🏢 Neste" if "neste" in result.metadata.tags else "❓ Unknown"
            
            # Relevance scoring with emojis
            score = result.relevance_score
            if score >= 0.8:
                relevance = "🎯 Very Relevant"
            elif score >= 0.6:
                relevance = "✅ Relevant"
            elif score >= 0.4:
                relevance = "⚠️ Somewhat Relevant"
            else:
                relevance = "❌ Low Relevance"
            
            # Display with rich formatting
            print(f'{i}. 📖 {result.metadata.title}')
            print(f'   {client} | {relevance} ({score:.3f})')
            print(f'   📄 Page ID: {result.metadata.page_id}')
            
            # Content preview (truncated for security)
            content = result.content.strip()
            if len(content) > 200:
                content = content[:200] + "..."
            print(f'   💬 Preview: {content}')
            print(f'   🔗 URL: {result.metadata.page_url}')
            print()
            
            formatted_results.append({
                'title': result.metadata.title,
                'score': score,
                'relevance': relevance,
                'url': result.metadata.page_url,
                'client': client.replace('🏢 ', ''),
                'preview': content
            })
        
        # Completion indicators
        print('='*60)
        print(f'✅ Search completed - {len(results)} results')
        
        # Update state
        state.runbooks = formatted_results
        state.status = "SUCCESS"
        state.add_performance_metric("search_duration", time.time() - start_time)
        
        return state
        
    except Exception as e:
        print(f'❌ Error during runbook search: {e}')
        state.status = "ERROR"
        state.error_details = str(e)
        return state
```

### Phase 3: Real Slack Integration Implementation

**Target**: Replace mock implementation in `notify_team_node` (lines 427-431)

```python
async def notify_team_node(self, state: WorkflowState) -> WorkflowState:
    """Send team notification with real Slack integration."""
    
    # Progress indicator
    print("📢 Preparing team notification...")
    
    # Build structured message content
    message_text = self._build_notification_message(state)
    
    # Progress update
    print(f"📝 Message prepared for {state.jira_key} ({state.status})")
    
    # REAL SLACK INTEGRATION - Replace lines 427-431
    if self.use_real_tools and self.slack_configured:
        from src.frameworks.graphmcp.clients.slack import SlackMCPClient
        
        print("🚀 Sending Slack notification...")
        
        try:
            slack_client = SlackMCPClient(self.config_path)
            result = await slack_client.post_message("C066PQYUYR4", message_text)  # #mc-dba-jira-notifications
            
            if result.get("success"):
                print(f"✅ Successfully sent {state.status} notification to Slack for {state.jira_key}")
                self.logger.log_info(f"✅ Slack notification sent successfully", extra={
                    "jira_key": state.jira_key,
                    "status": state.status,
                    "message_ts": result.get("message_ts")
                })
                state.slack_message_sent = True
                state.slack_message_ts = result.get("message_ts")
                
            else:
                print(f"⚠️ Failed to send Slack notification: {result.get('error')}")
                self.logger.log_warning(f"⚠️ Slack notification failed: {result.get('error')}")
                # Graceful fallback to mock
                print(f"🔄 Falling back to mock notification")
                self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
                state.slack_message_sent = False
                
        except Exception as e:
            print(f"❌ Slack integration error: {e}")
            self.logger.log_error(f"❌ Slack integration error: {e}")
            # Graceful fallback to mock
            print(f"🔄 Falling back to mock notification")
            self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
            state.slack_message_sent = False
            
    else:
        # Mock notification (development/testing)
        print("🧪 Using mock notification (development mode)")
        self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
        self.logger.log_debug(f"Notification content preview: {message_text[:100]}...")
        state.slack_message_sent = False
    
    print("📬 Team notification completed")
    return state

def _build_notification_message(self, state: WorkflowState) -> str:
    """Build structured Slack notification message."""
    
    if state.status == "SUCCESS":
        # Success notification with runbook recommendations
        runbook_list = "\n".join([
            f"• {r['title']} ({r['relevance']} - {r['score']:.1%})" 
            for r in state.runbooks[:3]  # Top 3 results
        ])
        
        message = f"""🎯 DB Runbook Finder - SUCCESS

📋 Incident: {state.jira_key} ({state.client_name})
📝 Query: "{state.search_query}"
⏱️ Processing Time: {state.processing_time:.1f}s

📖 Runbook Recommendations ({len(state.runbooks)} found):
{runbook_list}

🔗 Jira Ticket: {state.jira_url}
📊 Full details added to ticket description"""

    elif state.status == "GAP_DETECTED":
        # Gap detection notification
        message = f"""⚠️ DB Runbook Finder - GAP DETECTED

📋 Incident: {state.jira_key} ({state.client_name})
📝 Query: "{state.search_query}"
⏱️ Processing Time: {state.processing_time:.1f}s

❌ No relevant runbooks found
📝 Gap analysis added to ticket
🔍 Consider manual runbook creation

🔗 Jira Ticket: {state.jira_url}"""

    else:  # ERROR
        # Error notification
        message = f"""🚨 DB Runbook Finder - ERROR

📋 Incident: {state.jira_key} ({state.client_name})
📝 Query: "{state.search_query}"
⏱️ Processing Time: {state.processing_time:.1f}s

❌ Workflow failed: {state.error_details}
🔧 Technical team notified

🔗 Jira Ticket: {state.jira_url}"""

    return message
```

### Phase 4: Enhanced Progress Display Throughout Workflow

**Target**: Add rich progress formatting to all workflow nodes

```python
# Enhanced progress display patterns for all nodes

async def fetch_incident_node(self, state: WorkflowState) -> WorkflowState:
    """Fetch incident with progress display."""
    
    print(f"🎫 Fetching incident details for: {state.jira_key}")
    print("="*50)
    
    # ... existing logic with progress indicators
    if success:
        print(f"✅ Incident fetched: {state.incident_summary}")
        print(f"🏢 Client: {state.client_name}")
        print(f"📅 Created: {state.incident_created}")
    else:
        print(f"❌ Failed to fetch incident: {error}")
    
    print("="*50)
    return state

async def update_jira_with_results_node(self, state: WorkflowState) -> WorkflowState:
    """Update Jira with progress display."""
    
    print(f"🎯 Updating Jira ticket: {state.jira_key}")
    print("🔄 Formatting runbook recommendations...")
    
    # ... existing logic with progress indicators
    
    print(f"✅ Jira ticket updated successfully")
    print(f"📊 Added {len(state.runbooks)} runbook recommendations")
    
    return state
```

## Security Considerations

### Content Security Patterns

**1. Content Truncation**:
```python
# Always truncate content previews
content = result.content.strip()
if len(content) > 200:
    content = content[:200] + "..."
```

**2. Input Sanitization**:
```python
# Sanitize user input in progress messages
query = html.escape(state.search_query)
print(f'🔍 Searching: "{query}"')
```

**3. Sensitive Data Protection**:
```python
# Never display credentials or tokens
# Use environment variables for all sensitive configuration
# Log only non-sensitive metadata
```

**4. Slack Message Security**:
```python
# Use specific channel IDs instead of names
# Limit message content to business-relevant information
# No technical details or sensitive system information
```

## Error Handling Strategy

### Graceful Degradation Pattern

**Slack Integration Failures**:
1. **Primary**: Attempt GraphMCP SlackMCPClient integration
2. **Fallback**: Log warning and use mock notification
3. **Continue**: Never let Slack failures stop workflow execution
4. **Monitoring**: Log all failures for operational visibility

**ChromaDB Failures**:
1. **Empty Collection**: Handle gracefully with clear error messages
2. **Search Failures**: Provide fallback search patterns
3. **Connection Issues**: Retry with exponential backoff

**Progress Display Failures**:
1. **Rich Library Issues**: Fallback to basic print statements
2. **Emoji Support**: Detect terminal capabilities and adapt
3. **Console Errors**: Continue workflow with minimal progress display

## Implementation Tasks (Sequential Order)

### Task 1: Constructor and Configuration Setup
- [ ] Modify `DBRunbookFinderNodes.__init__()` to accept `config_path` parameter
- [ ] Update workflow initialization to pass MCP config path
- [ ] Add vector store initialization in constructor
- [ ] Verify MCP configuration file includes Slack server setup

### Task 2: ChromaDB Integration Enhancement
- [ ] Replace Confluence API calls with direct ChromaDB search in `search_runbooks_node`
- [ ] Add empty collection validation and error handling
- [ ] Implement rich progress display for search operations
- [ ] Add content truncation and security measures for previews

### Task 3: Real Slack Integration Implementation
- [ ] Replace mock implementation in `notify_team_node` (lines 427-431)
- [ ] Import and initialize `SlackMCPClient` with proper config path
- [ ] Implement message formatting for different workflow outcomes
- [ ] Add graceful fallback to mock logging on failures
- [ ] Add progress indicators for Slack operations

### Task 4: Enhanced Progress Display
- [ ] Add rich formatting to `fetch_incident_node`
- [ ] Add progress indicators to `update_jira_with_results_node`
- [ ] Implement emoji-based relevance indicators
- [ ] Add step headers and completion indicators throughout workflow

### Task 5: Testing and Validation
- [ ] Test with empty ChromaDB collection scenarios
- [ ] Test Slack integration failures and fallback behavior
- [ ] Validate progress display across different terminal types
- [ ] Test end-to-end workflow with real tools enabled

### Task 6: Documentation and Logging
- [ ] Update docstrings with new functionality
- [ ] Add structured logging for operational monitoring
- [ ] Document new environment variables and configuration
- [ ] Update README with new features and requirements

## Validation Gates (Executable)

### Code Quality and Style
```bash
# Syntax and style validation
cd manager && uv run ruff check src/usecases/db_runbook_finder/ --fix
cd manager && uv run mypy src/usecases/db_runbook_finder/
cd manager && uv run black src/usecases/db_runbook_finder/
```

### Unit Testing
```bash
# Run existing and new unit tests
cd manager && uv run pytest tests/unit/usecases/test_db_runbook_finder.py -v
cd manager && uv run pytest tests/unit/ -k "runbook" -v
```

### Integration Testing
```bash
# Test ChromaDB integration
cd manager && uv run pytest tests/integration/test_chromadb_integration.py -v

# Test Slack integration (with mocks)
cd manager && uv run pytest tests/integration/test_slack_integration.py -v
```

### Functional Testing
```bash
# Test workflow end-to-end
cd manager && python -m pytest tests/functional/test_db_runbook_finder_workflow.py -v

# Test with real tools (requires environment setup)
cd manager && python -c "
from usecases.db_runbook_finder.workflow import DBRunbookFinderWorkflow
workflow = DBRunbookFinderWorkflow('src/frameworks/graphmcp/clients/mcp_config.json', use_real_tools=True)
print('✅ Workflow initialization successful')
"
```

### Service Health Validation
```bash
# Verify service dependencies
cd manager && curl -f http://localhost:9123/health || echo "⚠️ Manager service not running"

# Check ChromaDB collection status
cd manager && python -c "
from tools.confluence.app.vector_store import VectorStore
vs = VectorStore(collection_name='mcdb-runbooks')
count = vs._collection.count()
print(f'📊 ChromaDB collection has {count} chunks')
assert count > 0, 'Collection is empty'
print('✅ ChromaDB collection validated')
"

# Test MCP configuration
cd manager && python -c "
import json
with open('src/frameworks/graphmcp/clients/mcp_config.json') as f:
    config = json.load(f)
assert 'ovr_slack' in config, 'Slack MCP server not configured'
print('✅ MCP configuration validated')
"
```

### GraphMCP Framework Testing
```bash
# GraphMCP framework tests (if applicable)
cd manager/src/frameworks/graphmcp && make test-all

# Workflow validation
cd manager/src/frameworks/graphmcp && make demo
```

## Success Criteria and Quality Metrics

### Functional Requirements
- [ ] Real Slack notifications sent to #mc-dba-jira-notifications (C066PQYUYR4)
- [ ] ChromaDB-based runbook search replaces Confluence API calls
- [ ] Rich progress display throughout entire workflow execution
- [ ] Graceful fallback to mock logging when Slack unavailable
- [ ] Security measures prevent sensitive data exposure

### Performance Requirements
- [ ] ChromaDB search operations complete in <50ms
- [ ] Slack message delivery confirmed within 5 seconds
- [ ] Progress display updates do not impact workflow performance
- [ ] Empty collection handling prevents workflow crashes

### Quality Requirements
- [ ] 100% test coverage for new functionality
- [ ] No regressions in existing workflow behavior
- [ ] Comprehensive error handling and logging
- [ ] Production-ready security measures implemented

### Operational Requirements  
- [ ] Environment variables properly documented
- [ ] MCP configuration includes all required servers
- [ ] Monitoring and alerting for Slack integration failures
- [ ] Clear fallback behavior when services unavailable

## Risk Assessment and Mitigation

### High-Risk Areas

**1. Slack API Integration Failures**
- **Risk**: Production notifications may fail silently
- **Mitigation**: Comprehensive error handling with mock fallback
- **Monitoring**: Log all Slack API responses and failures

**2. ChromaDB Empty Collection**
- **Risk**: Workflow crashes when collection is empty
- **Mitigation**: Collection count validation before search operations
- **Recovery**: Clear error messages and graceful degradation

**3. Progress Display Performance Impact**
- **Risk**: Rich formatting may slow down workflow execution
- **Mitigation**: Lightweight formatting with minimal terminal operations
- **Fallback**: Basic print statements if rich library issues occur

### Medium-Risk Areas

**4. MCP Configuration Issues**
- **Risk**: SlackMCPClient initialization may fail
- **Mitigation**: Configuration validation at startup
- **Recovery**: Clear error messages for configuration problems

**5. Environment Variable Management**
- **Risk**: Missing or incorrect environment variables
- **Mitigation**: Validation checks during initialization
- **Documentation**: Clear setup instructions in README

## PRP Success Confidence Score: 9/10

**Scoring Rationale:**

**Strengths (Score: 9):**
- ✅ **Comprehensive Context**: Complete codebase analysis with existing patterns
- ✅ **Clear Implementation Path**: Sequential tasks with detailed code examples
- ✅ **Executable Validation Gates**: All test commands are runnable and specific
- ✅ **Security Considerations**: Content truncation, input sanitization, environment variables
- ✅ **Error Handling Strategy**: Graceful degradation with clear fallback patterns
- ✅ **External Resources**: Up-to-date documentation links for MCP, Rich, ChromaDB
- ✅ **Production Patterns**: Based on existing successful implementations in codebase

**Minor Gaps (-1 point):**
- ⚠️ **Rich Library Integration**: May need additional testing across different terminal types
- ⚠️ **MCP Server Stability**: Depends on external MCP server reliability

**Overall Assessment:**
This PRP provides comprehensive context for successful one-pass implementation. The implementation plan is detailed, security considerations are thorough, and validation gates are executable. The risk assessment covers major failure scenarios with clear mitigation strategies.

**Confidence Level**: High confidence for successful implementation with minimal iterative refinement needed.