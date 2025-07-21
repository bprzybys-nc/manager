"""
Workflow nodes for DB Runbook Finder workflow.

This module contains all the individual workflow nodes that process
Jira tickets and find relevant runbooks through semantic search.
"""

import time
from typing import Dict, Any, List
from ...frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

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
    
    def __init__(self):
        """Initialize the nodes with logging configuration."""
        self.config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id="db_runbook_finder", config=self.config)

    async def fetch_incident_node(self, state: WorkflowState) -> WorkflowState:
        """Fetch incident details from Jira.
        
        This node retrieves detailed information about the Jira ticket
        including summary, description, and project details.
        
        Args:
            state: Current workflow state containing jira_key
            
        Returns:
            Updated state with incident_data populated
        """
        self.logger.log_step_start("fetch_incident", f"Fetching incident {state.jira_key}")
        start_time = time.time()
        
        try:
            # TODO: Replace with actual MCP client call
            # response = await self.mcp_client.call_tool(
            #     "jira", 
            #     "get_ticket_details", 
            #     {"issueIdOrKey": state.jira_key}
            # )
            
            # Mock response for development/testing
            mock_response = self._get_mock_jira_response(state.jira_key)
            
            # Extract relevant information from Jira response
            fields = mock_response.get("fields", {})
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
            
            duration = time.time() - start_time
            state.add_performance_metric("fetch_incident", duration)
            
            self.logger.log_step_end(
                "fetch_incident", 
                {"client": state.get_client_name(), "summary": state.get_incident_summary()},
                success=True
            )
            
            return state
            
        except Exception as e:
            duration = time.time() - start_time
            state.add_performance_metric("fetch_incident", duration)
            state.update_status("ERROR", f"Failed to fetch incident: {str(e)}")
            
            self.logger.log_step_end("fetch_incident", {"error": str(e)}, success=False)
            return state

    async def search_runbooks_node(self, state: WorkflowState) -> WorkflowState:
        """Search for relevant runbooks using vector search.
        
        This node performs semantic search against indexed Confluence runbooks
        in the AAVA and MCDBA spaces.
        
        Args:
            state: Current workflow state with incident_data
            
        Returns:
            Updated state with runbooks populated
        """
        self.logger.log_step_start("search_runbooks", "Performing vector search for runbooks")
        start_time = time.time()
        
        try:
            # Construct search query from incident data
            query = state.get_search_query()
            
            if not query:
                self.logger.log_info("No search query available, skipping search")
                state.runbooks = []
                duration = time.time() - start_time
                state.add_performance_metric("search_runbooks", duration)
                return state
            
            # TODO: Replace with actual MCP client call
            # response = await self.mcp_client.call_tool(
            #     "confluence",
            #     "vector_search",
            #     {
            #         "query": query,
            #         "space_keys": ["AAVA", "MCDBA"],
            #         "limit": 3
            #     }
            # )
            
            # Mock response for development/testing
            mock_response = self._get_mock_confluence_response(query, state.jira_key)
            
            # Store search results
            state.runbooks = mock_response.get("results", [])
            
            duration = time.time() - start_time
            state.add_performance_metric("search_runbooks", duration)
            
            self.logger.log_step_end(
                "search_runbooks",
                {
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "results_count": len(state.runbooks)
                },
                success=True
            )
            
            return state
            
        except Exception as e:
            duration = time.time() - start_time
            state.add_performance_metric("search_runbooks", duration)
            state.update_status("ERROR", f"Failed to search runbooks: {str(e)}")
            
            self.logger.log_step_end("search_runbooks", {"error": str(e)}, success=False)
            return state

    async def update_jira_with_results_node(self, state: WorkflowState) -> WorkflowState:
        """Update Jira ticket with runbook recommendations.
        
        This node formats the found runbooks into a human-readable comment
        and adds it to the Jira ticket.
        
        Args:
            state: Current workflow state with runbooks found
            
        Returns:
            Updated state with SUCCESS status
        """
        self.logger.log_step_start("update_jira_results", f"Adding results to {state.jira_key}")
        start_time = time.time()
        
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
                space = runbook.get("space_key", "Unknown")
                
                comment_lines.extend([
                    f"**{i}. {title}**",
                    f"   📊 Relevance: {relevance:.1%}",
                    f"   📚 Space: {space}",
                    f"   🔗 Link: {url}",
                    ""
                ])
            
            comment_lines.extend([
                "**Additional Information:**",
                f"- Search performed against: AAVA, MCDBA spaces",
                f"- Client: {state.get_client_name()}",
                f"- Processing time: {state.get_total_duration():.2f} seconds",
                "",
                "---",
                "*This recommendation was generated automatically by the DB Runbook Finder.*"
            ])
            
            comment_text = "\n".join(comment_lines)
            
            # TODO: Replace with actual MCP client call
            # await self.mcp_client.call_tool(
            #     "jira",
            #     "add_comment",
            #     {
            #         "issueIdOrKey": state.jira_key,
            #         "comment": comment_text
            #     }
            # )
            
            # Mock comment addition
            self.logger.log_info(f"Mock: Added comment to {state.jira_key} with {len(state.runbooks)} runbooks")
            
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
                f"- Searched spaces: AAVA, MCDBA",
                f"- Query used: {state.get_search_query()[:200]}{'...' if len(state.get_search_query()) > 200 else ''}",
                f"- Processing time: {state.get_total_duration():.2f} seconds",
                "",
                "---",
                "*Gap detection performed automatically by DB Runbook Finder.*"
            ]
            
            comment_text = "\n".join(gap_comment)
            
            # TODO: Replace with actual MCP client call
            # await self.mcp_client.call_tool(
            #     "jira",
            #     "add_comment",
            #     {
            #         "issueIdOrKey": state.jira_key,
            #         "comment": comment_text
            #     }
            # )
            
            # Mock comment addition
            self.logger.log_info(f"Mock: Added gap comment to {state.jira_key}")
            
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
            
            # TODO: Replace with actual MCP client call
            # await self.mcp_client.call_tool(
            #     "slack",
            #     "send_message",
            #     {
            #         "channel": "#mc-dba-jira-notifications",
            #         "text": message_text
            #     }
            # )
            
            # Mock notification
            self.logger.log_info(f"Mock: Sent {state.status} notification to Slack for {state.jira_key}")
            
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
        # Simulate different responses based on query content
        if "database" in query.lower() and "timeout" in query.lower():
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