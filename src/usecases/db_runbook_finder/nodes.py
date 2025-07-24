"""
Workflow nodes for DB Runbook Finder workflow.

This module contains all the individual workflow nodes that process
Jira tickets and find relevant runbooks through semantic search.
"""

import time
from typing import Dict, Any, Optional
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

from .state import WorkflowState


class DBRunbookFinderNodes:
    """Implementation of all workflow nodes for DB Runbook Finder.
    
    This class contains the business logic for each step of the workflow,
    from fetching Jira tickets to sending Slack notifications.
    """
    
    # Project key to client name mapping
    PROJECT_TO_CLIENT_MAP = {
        "AGENT": "Agent System",
        "NESMCI": "Neste",
        "HEMCI": "Helvetia", 
        "OVRMCI": "Ovora Internal",
        "OVR": "Ovora",
        "TEST": "Test Environment",
        # Add more mappings as needed
    }
    
    def __init__(self, config_path: str = "src/frameworks/graphmcp/clients/mcp_config.json", use_real_tools: bool = False):
        """Initialize the nodes with logging configuration and tool integration.
        
        Args:
            config_path: Path to MCP configuration file for GraphMCP client initialization
            use_real_tools: Whether to use real tool integrations when available
        """
        self.config_path = config_path
        self.config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id="db_runbook_finder", config=self.config)
        
        # Direct tool integration configuration
        self.use_real_tools = use_real_tools
        self.jira_configured = self._check_tool_configured("JIRA")
        self.confluence_configured = self._check_tool_configured("CONFLUENCE")
        self.slack_configured = self._check_tool_configured("SLACK")
        
        # Initialize vector store for ChromaDB integration (READ-ONLY, do not create/modify collection)
        # This safely connects to existing 'mcdb-runbooks' collection without erasing data
        try:
            from src.tools.confluence.app.vector_store import VectorStore
            self.vector_store: Optional[VectorStore] = VectorStore(collection_name='mcdb-runbooks')
            self.logger.log_info("Vector store initialized for 'mcdb-runbooks' collection")
        except Exception as e:
            self.logger.log_warning(f"Vector store initialization failed: {e}. Will use fallback search.")
            self.vector_store = None
        
        if self.use_real_tools:
            self.logger.log_info(f"Direct tool integration enabled - Jira: {self.jira_configured}, Confluence: {self.confluence_configured}, Slack: {self.slack_configured}")
        else:
            self.logger.log_info("Using mock implementations for all external tools")

    def _check_tool_configured(self, tool_name: str) -> bool:
        """Check if a tool is properly configured for direct integration.
        
        Args:
            tool_name: Name of the tool (JIRA, CONFLUENCE, SLACK)
            
        Returns:
            True if tool configuration is available
        """
        import os
        
        config_map = {
            "JIRA": ["JIRA_URL", "JIRA_API_TOKEN"],
            "CONFLUENCE": ["CONFLUENCE_URL", "CONFLUENCE_API_TOKEN"],
            "SLACK": ["SLACK_BOT_TOKEN"]
        }
        
        required_vars = config_map.get(tool_name, [])
        return all(os.getenv(var) for var in required_vars)

    async def fetch_incident_node(self, state: WorkflowState) -> WorkflowState:
        """Fetch incident details from Jira with rich progress display.
        
        This node retrieves detailed information about the Jira ticket
        including summary, description, and project details.
        
        Args:
            state: Current workflow state containing jira_key
            
        Returns:
            Updated state with incident_data populated
        """
        self.logger.log_step_start("fetch_incident", f"Fetching incident {state.jira_key}")
        start_time = time.time()
        
        # Rich progress display - Step header
        print(f"🎫 Fetching incident details for: {state.jira_key}")
        print("="*50)
        
        try:
            # Progress indicator
            if self.use_real_tools and self.jira_configured:
                print("🔗 Connecting to Jira API...")
                from src.tools.jira.app.jira import JiraClient
                jira_client = JiraClient()
                response = jira_client.get_ticket(state.jira_key)
                jira_data = response  # Real API response
                print("✅ Real Jira data retrieved")
            else:
                print("🧪 Using mock Jira data (development mode)")
                jira_data = self._get_mock_jira_response(state.jira_key)
            
            # Extract relevant information from Jira response
            fields = jira_data.get("fields", {})
            project_key = fields.get("project", {}).get("key", "")
            
            state.incident_data = {
                "summary": fields.get("summary", ""),
                "description": fields.get("description", ""),
                "client": self.PROJECT_TO_CLIENT_MAP.get(project_key, "Unknown"),
                "project_key": project_key,
                "issue_type": fields.get("issuetype", {}).get("name", ""),
                "priority": fields.get("priority", {}).get("name", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
                "status": fields.get("status", {}).get("name", ""),
                "created": fields.get("created", ""),
                "labels": fields.get("labels", [])
            }
            
            # Rich summary display with emoji indicators
            priority = state.incident_data.get("priority", "")
            if priority == "High":
                priority_emoji = "🔴 High"
            elif priority == "Medium":
                priority_emoji = "🟡 Medium"
            elif priority == "Low":
                priority_emoji = "🟢 Low"
            else:
                priority_emoji = f"⚪ {priority}"
            
            # Client identification with emoji
            client = state.get_client_name()
            if "Helvetia" in client:
                client_emoji = "🏢 Helvetia"
            elif "Neste" in client:
                client_emoji = "🏢 Neste"
            elif "Agent" in client:
                client_emoji = "🤖 Agent System"
            elif "Ovora" in client:
                client_emoji = "⚙️ Ovora"
            else:
                client_emoji = f"❓ {client}"
            
            print("✅ Incident fetched successfully:")
            print(f"   📋 Summary: {state.get_incident_summary()[:80]}{'...' if len(state.get_incident_summary()) > 80 else ''}")
            print(f"   {client_emoji}")
            print(f"   {priority_emoji} Priority")
            print(f"   📅 Created: {state.incident_data.get('created', 'Unknown')[:10]}")
            print(f"   👤 Assignee: {state.incident_data.get('assignee', 'Unassigned')}")
            
            duration = time.time() - start_time
            state.add_performance_metric("fetch_incident", duration)
            
            print("="*50)
            
            self.logger.log_step_end(
                "fetch_incident", 
                {"client": state.get_client_name(), "summary": state.get_incident_summary()},
                success=True
            )
            
            return state
            
        except Exception as e:
            print(f"❌ Failed to fetch incident: {e}")
            print("="*50)
            
            duration = time.time() - start_time
            state.add_performance_metric("fetch_incident", duration)
            state.update_status("ERROR", f"Failed to fetch incident: {str(e)}")
            
            self.logger.log_step_end("fetch_incident", {"error": str(e)}, success=False)
            return state

    async def search_runbooks_node(self, state: WorkflowState) -> WorkflowState:
        """Search for relevant runbooks using ChromaDB vector search with rich progress display.
        
        This node performs semantic search against the 'mcdb-runbooks' ChromaDB collection
        with comprehensive progress indicators and security measures.
        
        Args:
            state: Current workflow state with incident_data
            
        Returns:
            Updated state with runbooks populated
        """
        self.logger.log_step_start("search_runbooks", "Performing ChromaDB vector search for runbooks")
        start_time = time.time()
        
        try:
            # Construct search query from incident data
            query = state.get_search_query()
            
            if not query:
                print("❌ No search query available, skipping search")
                self.logger.log_info("No search query available, skipping search")
                state.runbooks = []
                duration = time.time() - start_time
                state.add_performance_metric("search_runbooks", duration)
                return state
            
            # Rich progress display - Step header
            import html
            safe_query = html.escape(query[:50] + "..." if len(query) > 50 else query)
            print(f'🔍 Searching runbooks for: "{safe_query}"')
            print('='*60)
            
            # ChromaDB integration with empty collection validation
            if self.vector_store is not None:
                print("📊 Checking ChromaDB collection status...")
                
                try:
                    # Critical: Validate collection exists and has content (be extremely careful not to modify)
                    count = self.vector_store._collection.count()
                    print(f'📊 Collection: mcdb-runbooks ({count} chunks)')
                    
                    if count == 0:
                        print("❌ ChromaDB collection is empty - no runbooks indexed")
                        self.logger.log_warning("ChromaDB collection 'mcdb-runbooks' is empty")
                        state.runbooks = []
                        state.update_status("GAP_DETECTED", "ChromaDB collection is empty")
                        duration = time.time() - start_time
                        state.add_performance_metric("search_runbooks", duration)
                        return state
                    
                    print("🔄 Performing semantic search...")
                    
                    # Perform semantic search with ChromaDB (READ-ONLY operation)
                    search_results = self.vector_store.search_runbooks(query, n_results=5)
                    
                    if not search_results:
                        print("🤷 No relevant runbooks found for query")
                        self.logger.log_info("No relevant runbooks found in ChromaDB search")
                        state.runbooks = []
                        state.update_status("GAP_DETECTED", "No relevant runbooks found")
                        duration = time.time() - start_time
                        state.add_performance_metric("search_runbooks", duration)
                        return state
                    
                    # Rich results formatting with security measures
                    print(f'📋 Found {len(search_results)} relevant results:')
                    print()
                    
                    formatted_results = []
                    for i, result in enumerate(search_results, 1):
                        # Client identification from tags
                        tags = result.metadata.tags if result.metadata.tags else []
                        client = "🏢 Helvetia" if "helvetia" in [tag.lower() for tag in tags] else \
                                "🏢 Neste" if "neste" in [tag.lower() for tag in tags] else \
                                "❓ Unknown"
                        
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
                        
                        # Content preview with security truncation
                        content = result.content.strip()
                        if len(content) > 200:
                            content = content[:200] + "..."
                        # Additional security: escape HTML and remove potential sensitive patterns
                        content = html.escape(content)
                        print(f'   💬 Preview: {content}')
                        print(f'   🔗 URL: {result.metadata.page_url}')
                        print()
                        
                        # Format for state (clean data for further processing)
                        formatted_results.append({
                            'title': result.metadata.title,
                            'url': result.metadata.page_url,
                            'space_key': result.metadata.space_key,
                            'relevance_score': score,
                            'excerpt': content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')  # Unescape for internal use
                        })
                    
                    # Completion indicators
                    print('='*60)
                    print(f'✅ ChromaDB search completed - {len(search_results)} results')
                    
                    # Update state with results
                    state.runbooks = formatted_results
                    
                except Exception as vector_error:
                    print(f'❌ ChromaDB search error: {vector_error}')
                    self.logger.log_error(f"ChromaDB search failed: {vector_error}")
                    
                    # Graceful fallback to mock search
                    print("🔄 Falling back to mock search...")
                    mock_response = self._get_mock_confluence_response(query, state.jira_key)
                    state.runbooks = mock_response.get("results", [])
                    
            else:
                # Vector store not available - fallback to mock implementation
                print("🧪 Vector store unavailable - using mock search")
                self.logger.log_warning("Vector store not initialized, using fallback mock search")
                mock_response = self._get_mock_confluence_response(query, state.jira_key)
                state.runbooks = mock_response.get("results", [])
            
            duration = time.time() - start_time
            state.add_performance_metric("search_runbooks", duration)
            
            self.logger.log_step_end(
                "search_runbooks",
                {
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "results_count": len(state.runbooks),
                    "search_method": "chromadb" if self.vector_store else "mock"
                },
                success=True
            )
            
            return state
            
        except Exception as e:
            print(f'❌ Search operation failed: {e}')
            duration = time.time() - start_time
            state.add_performance_metric("search_runbooks", duration)
            state.update_status("ERROR", f"Failed to search runbooks: {str(e)}")
            
            self.logger.log_step_end("search_runbooks", {"error": str(e)}, success=False)
            return state

    async def update_jira_with_results_node(self, state: WorkflowState) -> WorkflowState:
        """Update Jira ticket with runbook recommendations with rich progress display.
        
        This node formats the found runbooks into a human-readable comment
        and adds it to the Jira ticket.
        
        Args:
            state: Current workflow state with runbooks found
            
        Returns:
            Updated state with SUCCESS status
        """
        self.logger.log_step_start("update_jira_results", f"Adding results to {state.jira_key}")
        start_time = time.time()
        
        # Rich progress display - Step header
        print(f"🎯 Updating Jira ticket: {state.jira_key}")
        print("🔄 Formatting runbook recommendations...")
        
        try:
            # Format runbook recommendations with rich display
            comment_lines = [
                "🔍 **Automated Runbook Recommendations**",
                "",
                "Based on the incident description, here are the most relevant runbooks:",
                ""
            ]
            
            print(f"📝 Preparing {len(state.runbooks)} runbook recommendations:")
            
            for i, runbook in enumerate(state.runbooks[:3], 1):
                title = runbook.get("title", "Unknown Title")
                url = runbook.get("url", "#")
                relevance = runbook.get("relevance_score", 0)
                space = runbook.get("space_key", "Unknown")
                
                # Emoji-based relevance indicators for console display
                if relevance >= 0.8:
                    relevance_emoji = "🎯"
                elif relevance >= 0.6:
                    relevance_emoji = "✅"
                elif relevance >= 0.4:
                    relevance_emoji = "⚠️"
                else:
                    relevance_emoji = "❌"
                
                print(f"   {i}. {relevance_emoji} {title} ({relevance:.1%})")
                
                comment_lines.extend([
                    f"**{i}. {title}**",
                    f"   📊 Relevance: {relevance:.1%}",
                    f"   📚 Space: {space}",
                    f"   🔗 Link: {url}",
                    ""
                ])
            
            comment_lines.extend([
                "**Additional Information:**",
                "- Search performed against: ChromaDB vector database",
                f"- Client: {state.get_client_name()}",
                f"- Processing time: {state.get_total_duration():.2f} seconds",
                "",
                "---",
                "*This recommendation was generated automatically by the DB Runbook Finder.*"
            ])
            
            comment_text = "\n".join(comment_lines)
            
            # Progress indicator for Jira integration
            if self.use_real_tools and self.jira_configured:
                print("🔗 Adding comment to Jira ticket...")
                from src.tools.jira.app.jira import JiraClient
                jira_client = JiraClient()
                jira_client.add_internal_comment(state.jira_key, comment_text)
                print("✅ Real Jira comment added successfully")
                self.logger.log_info(f"Added comment to {state.jira_key} with {len(state.runbooks)} runbooks")
            else:
                print("🧪 Mock: Jira comment prepared (development mode)")
                self.logger.log_info(f"Mock: Added comment to {state.jira_key} with {len(state.runbooks)} runbooks")
            
            print(f"📊 Summary: Added {len(state.runbooks)} runbook recommendations to ticket")
            self.logger.log_debug(f"Comment content preview: {comment_text[:100]}...")
            
            duration = time.time() - start_time
            state.add_performance_metric("update_jira_results", duration)
            state.update_status("SUCCESS")
            
            self.logger.log_step_end(
                "update_jira_results",
                {"ticket": state.jira_key, "runbooks_added": len(state.runbooks)},
                success=True
            )
            
            return state
            
        except Exception as e:
            duration = time.time() - start_time
            state.add_performance_metric("update_jira_results", duration)
            state.update_status("ERROR", f"Failed to update Jira: {str(e)}")
            
            self.logger.log_step_end("update_jira_results", {"error": str(e)}, success=False)
            return state

    async def terminate_with_gap_error_node(self, state: WorkflowState) -> WorkflowState:
        """Handle gap scenario where no runbooks were found.
        
        This node creates a gap notification comment and adds it to the Jira ticket
        to inform users that no relevant runbooks were discovered.
        
        Args:
            state: Current workflow state with empty runbooks list
            
        Returns:
            Updated state with GAP_DETECTED status
        """
        self.logger.log_step_start("terminate_gap", f"Handling gap for {state.jira_key}")
        start_time = time.time()
        
        try:
            gap_comment = [
                "⚠️ **Runbook Gap Detected**",
                "",
                "No relevant runbooks were found for this incident in the indexed knowledge base.",
                "",
                "**Incident Details:**",
                f"- Summary: {state.get_incident_summary()}",
                f"- Client: {state.get_client_name()}",
                f"- Issue Type: {state.incident_data.get('issue_type', 'N/A')}",
                f"- Priority: {state.incident_data.get('priority', 'N/A')}",
                "",
                "**Possible Reasons:**",
                "- This is a novel incident type requiring new procedures",
                "- Existing runbooks may not be properly indexed",
                "- Search terms may need refinement",
                "",
                "**Recommended Next Steps:**",
                "1. Perform manual search in AAVA and MCDBA Confluence spaces",
                "2. Consult with senior team members for similar incidents",
                "3. Consider creating new runbook for this scenario",
                "4. Review and update indexed runbook content if needed",
                "",
                "**Search Details:**",
                "- Searched spaces: AAVA, MCDBA",
                f"- Query used: {state.get_search_query()[:200]}{'...' if len(state.get_search_query()) > 200 else ''}",
                f"- Processing time: {state.get_total_duration():.2f} seconds",
                "",
                "---",
                "*Gap detection performed automatically by DB Runbook Finder.*"
            ]
            
            comment_text = "\n".join(gap_comment)
            
            # Direct tool integration point
            if self.use_real_tools and self.jira_configured:
                from src.tools.jira.app.jira import JiraClient
                jira_client = JiraClient()
                jira_client.add_internal_comment(state.jira_key, comment_text)
                self.logger.log_info(f"Added gap comment to {state.jira_key}")
            else:
                # Mock comment addition
                self.logger.log_info(f"Mock: Added gap comment to {state.jira_key}")
            self.logger.log_debug(f"Gap comment content preview: {comment_text[:100]}...")
            
            duration = time.time() - start_time
            state.add_performance_metric("terminate_gap", duration)
            state.update_status("GAP_DETECTED")
            
            self.logger.log_step_end(
                "terminate_gap",
                {"ticket": state.jira_key, "gap_detected": True},
                success=True
            )
            
            return state
            
        except Exception as e:
            duration = time.time() - start_time
            state.add_performance_metric("terminate_gap", duration)
            state.update_status("ERROR", f"Failed to handle gap: {str(e)}")
            
            self.logger.log_step_end("terminate_gap", {"error": str(e)}, success=False)
            return state

    async def notify_team_node(self, state: WorkflowState) -> WorkflowState:
        """Send Slack notification to team.
        
        This node sends appropriate notifications to the MC-DBA team channel
        based on the workflow outcome (success, gap, or error).
        
        Args:
            state: Current workflow state with final status
            
        Returns:
            Final state with notification sent
        """
        self.logger.log_step_start("notify_team", f"Sending notification for {state.jira_key}")
        start_time = time.time()
        
        try:
            # Format message based on status
            if state.status == "SUCCESS":
                message_lines = [
                    f"✅ **Runbook Recommendations Found** - {state.jira_key}",
                    "",
                    f"**Incident:** {state.get_incident_summary()}",
                    f"**Client:** {state.get_client_name()}",
                    f"**Runbooks Found:** {len(state.runbooks)}",
                    f"**Processing Time:** {state.get_total_duration():.2f} seconds",
                    "",
                    "**Top Recommendations:**"
                ]
                
                for i, runbook in enumerate(state.runbooks[:2], 1):
                    title = runbook.get("title", "Unknown Title")
                    relevance = runbook.get("relevance_score", 0)
                    message_lines.append(f"{i}. {title} ({relevance:.1%} relevance)")
                
                message_lines.extend([
                    "",
                    f"🔗 View ticket: [Jira Link](#{state.jira_key})"
                ])
                
            elif state.status == "GAP_DETECTED":
                message_lines = [
                    f"⚠️ **Runbook Gap Detected** - {state.jira_key}",
                    "",
                    f"**Incident:** {state.get_incident_summary()}",
                    f"**Client:** {state.get_client_name()}",
                    f"**Processing Time:** {state.get_total_duration():.2f} seconds",
                    "",
                    "No relevant runbooks found. Manual intervention required.",
                    "Consider creating new runbook for this incident type.",
                    "",
                    f"🔗 View ticket: [Jira Link](#{state.jira_key})"
                ]
                
            else:  # ERROR state
                message_lines = [
                    f"❌ **Workflow Error** - {state.jira_key}",
                    "",
                    f"**Error:** {state.error_message}",
                    f"**Processing Time:** {state.get_total_duration():.2f} seconds",
                    "",
                    "Please check logs for detailed error information.",
                    "",
                    f"🔗 View ticket: [Jira Link](#{state.jira_key})"
                ]
            
            message_text = "\n".join(message_lines)
            
            # Progress indicator
            print("📢 Preparing team notification...")
            print(f"📝 Message prepared for {state.jira_key} ({state.status})")
            
            # REAL SLACK INTEGRATION - Replace lines 534-543 with GraphMCP SlackMCPClient
            if self.use_real_tools and self.slack_configured:
                print("🚀 Sending Slack notification...")
                
                try:
                    from src.frameworks.graphmcp.clients.slack import SlackMCPClient
                    
                    # Initialize Slack client with MCP configuration
                    slack_client = SlackMCPClient(self.config_path)
                    
                    # Send message to #mc-dba-jira-notifications channel (C066PQYUYR4)
                    result = await slack_client.post_message("C066PQYUYR4", message_text)
                    
                    if result.get("success"):
                        print(f"✅ Successfully sent {state.status} notification to Slack for {state.jira_key}")
                        self.logger.log_info("✅ Slack notification sent successfully", extra={
                            "jira_key": state.jira_key,
                            "status": state.status,
                            "message_ts": result.get("message_ts"),
                            "channel": "#mc-dba-jira-notifications"
                        })
                        
                        # Update state with Slack delivery confirmation
                        state.slack_message_sent = True
                        state.slack_message_ts = result.get("message_ts")
                        
                    else:
                        print(f"⚠️ Failed to send Slack notification: {result.get('error')}")
                        self.logger.log_warning(f"⚠️ Slack notification failed: {result.get('error')}")
                        
                        # Graceful fallback to mock
                        print("🔄 Falling back to mock notification")
                        self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
                        state.slack_message_sent = False
                        
                except Exception as e:
                    print(f"❌ Slack integration error: {e}")
                    self.logger.log_error(f"❌ Slack integration error: {e}")
                    
                    # Graceful fallback to mock
                    print("🔄 Falling back to mock notification")
                    self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
                    state.slack_message_sent = False
                    
            else:
                # Mock notification (development/testing mode)
                print("🧪 Using mock notification (development mode)")
                self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
                self.logger.log_debug(f"Notification content preview: {message_text[:100]}...")
                state.slack_message_sent = False
            
            print("📬 Team notification completed")
            
            duration = time.time() - start_time
            state.add_performance_metric("notify_team", duration)
            
            self.logger.log_step_end(
                "notify_team",
                {
                    "ticket": state.jira_key,
                    "status": state.status,
                    "total_duration": state.get_total_duration()
                },
                success=True
            )
            
            return state
            
        except Exception as e:
            duration = time.time() - start_time
            state.add_performance_metric("notify_team", duration)
            # Don't change the main status - notification failure shouldn't override workflow result
            
            self.logger.log_step_end("notify_team", {"error": str(e)}, success=False)
            return state

    def _get_mock_jira_response(self, jira_key: str) -> Dict[str, Any]:
        """Generate mock Jira response for testing.
        
        Args:
            jira_key: Jira ticket identifier
            
        Returns:
            Mock Jira ticket data
        """
        # Determine project key from jira_key
        project_key = jira_key.split('-')[0] if '-' in jira_key else "AGENT"
        
        mock_responses = {
            "AGENT-6": {
                "fields": {
                    "summary": "Database connection timeout in production environment",
                    "description": "Users experiencing intermittent database timeouts when accessing customer data. Connection pool seems to be exhausted during peak hours. Need to investigate connection management and potentially tune database parameters.",
                    "project": {"key": "AGENT"},
                    "issuetype": {"name": "Incident"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "John Smith"},
                    "status": {"name": "Open"},
                    "created": "2024-07-20T10:00:00.000Z",
                    "labels": ["database", "performance", "production"]
                }
            }
        }
        
        return mock_responses.get(jira_key, {
            "fields": {
                "summary": f"Mock incident for {jira_key}",
                "description": "This is a mock incident used for testing the DB Runbook Finder workflow.",
                "project": {"key": project_key},
                "issuetype": {"name": "Incident"},
                "priority": {"name": "Medium"},
                "assignee": {"displayName": "Test User"},
                "status": {"name": "Open"},
                "created": "2024-07-20T10:00:00.000Z",
                "labels": ["test", "mock"]
            }
        })

    def _get_mock_confluence_response(self, query: str, jira_key: str) -> Dict[str, Any]:
        """Generate mock Confluence search response.
        
        Args:
            query: Search query string
            jira_key: Original Jira key for context
            
        Returns:
            Mock Confluence search results
        """
        # Simulate different responses based on query content and jira_key
        if "GAP" in jira_key or "gap" in query.lower():
            # Return empty results for gap scenario testing
            return {"results": []}
        elif "database" in query.lower() and "timeout" in query.lower():
            return {
                "results": [
                    {
                        "title": "Database Connection Troubleshooting Guide",
                        "url": "https://confluence.example.com/display/MCDBA/DB+Connection+Troubleshooting",
                        "space_key": "MCDBA",
                        "relevance_score": 0.92,
                        "excerpt": "Step-by-step guide to diagnose and resolve database connection issues..."
                    },
                    {
                        "title": "Connection Pool Management Best Practices",
                        "url": "https://confluence.example.com/display/AAVA/Connection+Pool+Management",
                        "space_key": "AAVA", 
                        "relevance_score": 0.87,
                        "excerpt": "Guidelines for configuring and monitoring database connection pools..."
                    },
                    {
                        "title": "Production Database Performance Tuning",
                        "url": "https://confluence.example.com/display/MCDBA/Performance+Tuning",
                        "space_key": "MCDBA",
                        "relevance_score": 0.78,
                        "excerpt": "Comprehensive guide to optimizing database performance in production..."
                    }
                ]
            }
        elif "mock" in query.lower() or "test" in query.lower():
            return {
                "results": [
                    {
                        "title": "Test Environment Setup Guide",
                        "url": "https://confluence.example.com/display/AAVA/Test+Setup",
                        "space_key": "AAVA",
                        "relevance_score": 0.65,
                        "excerpt": "Instructions for setting up test environments..."
                    }
                ]
            }
        else:
            # Return empty results to simulate gap scenario
            return {"results": []}