FEATURE:
Migrate DB Runbook Finder from MCP Slack Integration to Direct Communication Tool Integration

This feature involves a comprehensive migration of the DB Runbook Finder workflow to use the proven working communication tool approach instead of the current MCP-based Slack integration. The migration includes:

1. **Tool Migration**: Replace current communication tools with proven working versions
   - Hard overwrite `src/tools/communication` with `src/tools/communication_536ab1c` 
   - Hard overwrite `src/usecases/db_incident_assistant` with `src/usecases/db_incident_assistant_536ab1c`

2. **Integration Testing**: Verify compatibility and fix issues
   - Test communication tool functionality in DB Runbook Finder context
   - Fix any issues arising from the tool overwrite
   - Ensure all existing tests pass

3. **Workflow Integration**: Update DB Runbook Finder to use direct communication
   - Replace MCP Slack integration with direct communication tool calls
   - Remove SLACK_TEAM_ID dependency 
   - Use proven BOT_TOKEN, APP_TOKEN, CHANNEL approach
   - Maintain all existing functionality (Jira comments, Confluence search, runbook recommendations)

4. **Demo Validation**: Ensure full end-to-end workflow works
   - Test complete workflow from Jira ticket fetch to Slack notification
   - Verify runbook search, relevance scoring, and internal Jira comments work
   - Confirm Slack notifications post successfully to #mc-dba-jira-notifications

5. **Cleanup**: Remove obsolete functionality and maintain clean codebase
   - Remove unused MCP-related code
   - Delete test files and temporary implementations
   - Ensure all tests pass after cleanup

EXAMPLES:
From examples in the codebase that demonstrate the patterns needed:

1. **Friend's Working Communication Tool** (`src/tools/communication_536ab1c/`):
   - `app/slack.py`: Direct Slack integration without MCP, using sync_app.client.chat_postMessage()
   - `app/api.py`: FastAPI integration with proper async lifecycle management
   - Environment variables: SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_CHANNEL (no SLACK_TEAM_ID)

2. **Friend's Working Use Case** (`src/usecases/db_incident_assistant_536ab1c/`):
   - `app/main.py`: Demonstrates direct communication tool usage in workflows
   - Shows proper OutboundCommunication class integration with send_status_update() and send_question()
   - Proves the communication approach works in production

3. **Current DB Runbook Finder Implementation** (`src/usecases/db_runbook_finder/`):
   - `workflow.py`: Current MCP-based Slack integration that needs migration
   - `nodes.py`: Runbook search and Jira integration that should remain unchanged
   - `tests/`: Comprehensive test suite that needs updates for new communication approach

4. **Test Evidence** (`src/usecases/db_runbook_finder/test_friend_simple.py`):
   - Proven working direct API approach: curl calls to slack.com/api/chat.postMessage
   - Successful authentication and posting to #mc-dba-jira-notifications channel
   - Demonstrates exact token format and API usage patterns

DOCUMENTATION:
1. **CLAUDE.md**: Project-wide development guidance and architecture patterns
2. **Manager CLAUDE.md**: Specific development scope and boundaries for manager component  
3. **Context Engineering Documentation** (`context-engineering/`):
   - `README.md`: Complete Manager context engineering system overview
   - `examples/`: Implementation patterns and best practices library
   - `commands/generate-prp.md` and `execute-prp.md`: PRP workflow automation

4. **Slack API Documentation**: 
   - Slack Bolt for Python documentation for understanding AsyncApp vs App usage
   - chat.postMessage API reference for direct posting approach
   - WebClient vs socket mode for understanding the friend's sync approach

5. **Existing Test Documentation**:
   - `src/usecases/db_runbook_finder/tests/test_slack_communication_simple.py`: Interface verification patterns
   - Test evidence showing exact environment variable requirements and API call patterns

OTHER CONSIDERATIONS:
1. **Critical Success Factors**:
   - Bot must remain added to #mc-dba-jira-notifications channel
   - Environment variables must use .env file (not system env vars) with load_dotenv(override=True)
   - Async event loop handling must be properly managed in Slack client initialization

2. **Potential Gotchas**:
   - Import path changes after tool migration: update all `from src.tools.communication` references
   - TaskDB dependency: friend's tool requires TaskDB instance, ensure proper mocking in tests
   - Async vs sync usage: friend uses both AsyncApp and App, workflow should use sync methods (create_thread, send_message)
   - Threading considerations: friend's tool uses threading for button responses

3. **Environment Variable Requirements**:
   - Remove SLACK_TEAM_ID from workflow (not needed in direct approach)
   - Ensure SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_CHANNEL are correctly loaded
   - Test environment variables loading with load_dotenv(override=True) to override system vars

4. **Testing Strategy**:
   - Maintain existing comprehensive test coverage
   - Update import paths in test files
   - Add integration tests for new communication approach
   - Preserve runbook search, Jira integration, and vector database functionality tests

5. **Workflow Integration Points**:
   - Replace SlackMCPClient usage in workflow.py with direct Slack class usage
   - Update notification sending in workflow to use create_thread() and send_message()
   - Maintain existing message formatting and runbook result presentation
   - Ensure internal Jira comments functionality remains unchanged

6. **Performance and Reliability**:
   - Direct API approach should be more reliable than MCP
   - No GraphMCP dependency for Slack integration
   - Simpler error handling with direct HTTP responses
   - Maintain <50ms response times for runbook search functionality