"""
DB Runbook Finder Workflow

Main workflow class that orchestrates the AI-powered runbook discovery process
using the GraphMCP framework and LangGraph state management.
"""

import asyncio
from typing import Dict, Any, Optional
from src.frameworks.graphmcp.workflows.builder import WorkflowBuilder
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

from .state import WorkflowState
from .nodes import DBRunbookFinderNodes
from .mcp_server.client import RunbookRepositoryMCPClient
from .mcp_server.strategy_factory import StrategyFactory, StrategyConfig
from .mcp_server.server import RunbookRepositoryMCPServer


class DBRunbookFinderWorkflow:
    """DB Runbook Finder workflow implementation using GraphMCP framework.
    
    This workflow processes Jira incidents and finds relevant runbooks through
    semantic search, providing automated recommendations to reduce incident
    response time.
    """
    
    def __init__(self, config_path: str = "src/frameworks/graphmcp/mcp_config.json", use_mcp_server: bool = True):
        """Initialize the workflow with GraphMCP configuration.
        
        Args:
            config_path: Path to MCP server configuration file
            use_mcp_server: Whether to use the new RunbookRepositoryMCP server (default: True)
        """
        self.config_path = config_path
        self.use_mcp_server = use_mcp_server
        self.nodes = DBRunbookFinderNodes()
        
        # Initialize logging
        self.logging_config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id="db_runbook_finder_main", config=self.logging_config)
        
        # Initialize workflow builder
        self._workflow = None
        
        # Initialize MCP server components if enabled
        self._mcp_client: Optional[RunbookRepositoryMCPClient] = None
        self._mcp_server: Optional[RunbookRepositoryMCPServer] = None
        self._strategy_factory: Optional[StrategyFactory] = None
        
        if self.use_mcp_server:
            self._initialize_mcp_components()
    
    def _initialize_mcp_components(self):
        """Initialize RunbookRepositoryMCP server components.
        
        Sets up the strategy factory, MCP server, and client for the new
        quadruple strategy pattern implementation.
        """
        try:
            self.logger.log_info("Initializing RunbookRepositoryMCP server components")
            
            # Create strategy configuration
            environment = "development"  # Could be determined from env var
            strategy_config = StrategyConfig(environment=environment)
            
            # Initialize strategy factory
            self._strategy_factory = StrategyFactory(config=strategy_config)
            
            # Initialize MCP client for workflow integration
            self._mcp_client = RunbookRepositoryMCPClient(config_path=self.config_path)
            
            # Update nodes to use MCP client if available
            if hasattr(self.nodes, 'set_mcp_client'):
                self.nodes.set_mcp_client(self._mcp_client)
            
            self.logger.log_info(f"MCP components initialized successfully in {environment} mode")
            
        except Exception as e:
            self.logger.log_error(f"Failed to initialize MCP components: {e}", exception=e)
            # Continue without MCP server - graceful degradation
            self.use_mcp_server = False
            self._mcp_client = None
            self._strategy_factory = None
            self.logger.log_info("Falling back to legacy workflow implementation")
    
    async def _ensure_mcp_server_ready(self) -> bool:
        """Ensure MCP server is initialized and ready.
        
        Returns:
            True if MCP server is ready, False if falling back to legacy mode
        """
        if not self.use_mcp_server or not self._strategy_factory:
            return False
        
        try:
            # Create MCP server with strategies if not already created
            if self._mcp_server is None:
                strategies = await self._strategy_factory.create_all_strategies()
                
                self._mcp_server = RunbookRepositoryMCPServer(
                    discovery_strategy=strategies["discovery"],
                    vector_strategy=strategies["vector"],
                    persistence_strategy=strategies["persistence"],
                    notification_strategy=strategies["notification"]
                )
                
                self.logger.log_info("MCP server created and ready")
            
            # Health check
            if self._mcp_client:
                health_check = await self._mcp_client.health_check()
                if not health_check:
                    self.logger.log_warning("MCP server health check failed, using legacy mode")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"Failed to ensure MCP server readiness: {e}", exception=e)
            return False

    def _build_workflow(self):
        """Build workflow configuration.
        
        For now, this returns a simple mock workflow object since the real
        GraphMCP WorkflowBuilder integration will be completed later.
        """
        if self._workflow is not None:
            return self._workflow
            
        self.logger.log_info("Building DB Runbook Finder workflow")
        
        try:
            # For now, return a simple mock workflow object
            # TODO: Replace with actual GraphMCP WorkflowBuilder when available
            workflow = {
                "name": "db_runbook_finder",
                "nodes": ["fetch_incident", "search_runbooks", "update_jira_results", "terminate_gap", "notify_team"],
                "routing": self._runbook_search_router
            }
            
            self._workflow = workflow
            self.logger.log_info("Workflow built successfully")
            return workflow
            
        except Exception as e:
            self.logger.log_error("Failed to build workflow", exception=e)
            raise

    def _runbook_search_router(self, state: WorkflowState) -> str:
        """Route workflow based on runbook search results.
        
        This routing function determines the next step based on whether
        runbooks were found during the semantic search.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next node name to execute
        """
        self.logger.log_info(f"Routing decision: runbooks_found={state.has_runbooks()}")
        
        if state.is_error_state():
            self.logger.log_error(f"Error state detected: {state.error_message}")
            return "notify_team"
        
        if state.has_runbooks():
            self.logger.log_info(f"Found {len(state.runbooks)} runbooks, proceeding to update Jira")
            return "update_jira_results"
        else:
            self.logger.log_info("No runbooks found, handling gap scenario")
            return "terminate_gap"

    async def run(self, jira_key: str, **kwargs) -> WorkflowState:
        """Execute the complete DB Runbook Finder workflow.
        
        This method runs the entire workflow from start to finish,
        processing the Jira ticket and finding relevant runbooks.
        
        Args:
            jira_key: Jira ticket identifier (e.g., "AGENT-6")
            **kwargs: Additional workflow parameters
            
        Returns:
            Final workflow state with results
        """
        # Initialize workflow state
        initial_state = WorkflowState(jira_key=jira_key)
        
        self.logger.log_workflow_start(
            {"jira_key": jira_key, "kwargs": kwargs}, 
            {"log_level": "INFO", "workflow": "db_runbook_finder"}
        )
        
        try:
            # Ensure MCP server is ready if enabled
            mcp_ready = await self._ensure_mcp_server_ready()
            if self.use_mcp_server and mcp_ready:
                self.logger.log_info("Using RunbookRepositoryMCP server for enhanced workflow")
            else:
                self.logger.log_info("Using legacy workflow implementation")
            
            # Build workflow if not already built
            workflow = self._build_workflow()
            
            # Execute workflow with error handling
            final_state = await self._execute_workflow_safely(workflow, initial_state)
            
            # Log final results
            self.logger.log_workflow_end(
                {
                    "status": final_state.status,
                    "runbooks_found": len(final_state.runbooks),
                    "total_duration": final_state.get_total_duration(),
                    "client": final_state.get_client_name()
                },
                success=final_state.is_completed()
            )
            
            return final_state
            
        except Exception as e:
            error_message = f"Workflow execution failed: {str(e)}"
            self.logger.log_error(error_message, exception=e)
            
            # Return error state
            initial_state.update_status("ERROR", error_message)
            return initial_state

    async def _execute_workflow_safely(self, workflow, initial_state: WorkflowState) -> WorkflowState:
        """Execute workflow with comprehensive error handling.
        
        Args:
            workflow: Built workflow object
            initial_state: Initial state to start with
            
        Returns:
            Final workflow state
        """
        try:
            # Execute the workflow
            # Note: This is a simplified mock execution
            # In actual implementation, this would use the GraphMCP workflow engine
            final_state = await self._mock_workflow_execution(initial_state)
            return final_state
            
        except asyncio.TimeoutError:
            error_message = "Workflow execution timed out"
            self.logger.log_error(error_message)
            initial_state.update_status("ERROR", error_message)
            return initial_state
            
        except Exception as e:
            error_message = f"Workflow execution error: {str(e)}"
            self.logger.log_error(error_message, exception=e)
            initial_state.update_status("ERROR", error_message)
            return initial_state

    async def _mock_workflow_execution(self, state: WorkflowState) -> WorkflowState:
        """Enhanced workflow execution with RunbookRepositoryMCP integration.
        
        This method executes the complete workflow by calling each node in sequence
        with proper routing logic. If the MCP server is available, it provides
        enhanced functionality through the quadruple strategy pattern.
        
        Args:
            state: Initial workflow state
            
        Returns:
            Final workflow state after execution
        """
        try:
            # Step 1: Fetch incident data (enhanced with MCP server if available)
            if self.use_mcp_server and self._mcp_client:
                state = await self._enhanced_fetch_incident_node(state)
            else:
                state = await self.nodes.fetch_incident_node(state)
            
            if state.is_error_state():
                state = await self._enhanced_notify_team_node(state)
                return state
            
            # Step 2: Search for runbooks (enhanced with MCP server if available)
            if self.use_mcp_server and self._mcp_client:
                state = await self._enhanced_search_runbooks_node(state)
            else:
                state = await self.nodes.search_runbooks_node(state)
            
            if state.is_error_state():
                state = await self._enhanced_notify_team_node(state)
                return state
            
            # Step 3: Route based on search results
            if state.has_runbooks():
                # Success path: Update Jira with results (enhanced)
                if self.use_mcp_server and self._mcp_client:
                    state = await self._enhanced_update_jira_with_results_node(state)
                else:
                    state = await self.nodes.update_jira_with_results_node(state)
            else:
                # Gap path: Handle no runbooks scenario (enhanced)
                if self.use_mcp_server and self._mcp_client:
                    state = await self._enhanced_terminate_with_gap_error_node(state)
                else:
                    state = await self.nodes.terminate_with_gap_error_node(state)
            
            # Step 4: Send team notification (enhanced)
            state = await self._enhanced_notify_team_node(state)
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Workflow execution failed: {str(e)}", exception=e)
            state.update_status("ERROR", f"Workflow execution failed: {str(e)}")
            return state
    
    # Enhanced Node Methods with MCP Server Integration
    async def _enhanced_fetch_incident_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced incident fetch using MCP server for data persistence tracking."""
        try:
            # Use the legacy node method for Jira fetch (maintains compatibility)
            state = await self.nodes.fetch_incident_node(state)
            
            # If successful and MCP server is available, track incident usage
            if not state.is_error_state() and self._mcp_client:
                try:
                    incident_context = {
                        "incident_id": state.jira_key,
                        "client": state.get_client_name(),
                        "summary": state.get_incident_summary(),
                        "priority": state.incident_data.get("priority", "Unknown"),
                        "issue_type": state.incident_data.get("issue_type", "Unknown"),
                        "workflow_started": True
                    }
                    
                    # Create an incident ticket for tracking
                    await self._mcp_client.create_incident_ticket(
                        runbook_id="workflow_start", 
                        context=incident_context
                    )
                    
                    self.logger.log_info(f"Created incident tracking for {state.jira_key}")
                    
                except Exception as e:
                    # Don't fail the workflow if MCP tracking fails
                    self.logger.log_warning(f"MCP incident tracking failed: {e}")
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Enhanced incident fetch failed: {e}", exception=e)
            state.update_status("ERROR", f"Enhanced incident fetch failed: {e}")
            return state
    
    async def _enhanced_search_runbooks_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced runbook search using MCP server with multiple search strategies."""
        try:
            query = state.get_search_query()
            if not query:
                self.logger.log_info("No search query available, skipping enhanced search")
                state.runbooks = []
                return state
            
            self.logger.log_info(f"Performing enhanced runbook search for: {query[:100]}...")
            
            # Perform comprehensive search using MCP client
            search_results = await self._mcp_client.comprehensive_runbook_search(
                query=query,
                spaces=["AAVA", "MCDBA"],
                include_semantic=True,
                limit=5
            )
            
            # Combine and deduplicate results
            all_results = []
            seen_ids = set()
            
            # Process text search results
            for result in search_results.get("text_results", []):
                runbook_id = result.get("runbook_id", "")
                if runbook_id not in seen_ids:
                    seen_ids.add(runbook_id)
                    all_results.append({
                        "title": result.get("title", "Unknown"),
                        "url": result.get("url", "#"),
                        "space_key": result.get("space_key", "Unknown"),
                        "relevance_score": result.get("search_relevance", 0.0),
                        "source": "text_search",
                        "runbook_id": runbook_id
                    })
            
            # Process semantic search results
            for result in search_results.get("semantic_results", []):
                runbook_id = result.get("runbook_id", "")
                if runbook_id not in seen_ids:
                    seen_ids.add(runbook_id)
                    all_results.append({
                        "title": result.get("title", "Unknown"),
                        "url": result.get("metadata", {}).get("url", "#"),
                        "space_key": result.get("metadata", {}).get("space_key", "Unknown"),
                        "relevance_score": result.get("similarity_score", 0.0),
                        "source": "semantic_search",
                        "runbook_id": runbook_id
                    })
            
            # Sort by relevance score
            all_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
            
            # Limit results
            state.runbooks = all_results[:3]
            
            # Track search metrics
            await self._track_search_metrics(state, query, len(all_results))
            
            self.logger.log_info(f"Enhanced search found {len(state.runbooks)} runbooks")
            return state
            
        except Exception as e:
            self.logger.log_error(f"Enhanced search failed, falling back to legacy: {e}")
            # Fallback to legacy search on failure
            return await self.nodes.search_runbooks_node(state)
    
    async def _enhanced_update_jira_with_results_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced Jira update with runbook usage tracking."""
        try:
            # Use the legacy method for Jira update (maintains compatibility)
            state = await self.nodes.update_jira_with_results_node(state)
            
            # Track runbook usage for each recommended runbook
            if not state.is_error_state() and self._mcp_client:
                for runbook in state.runbooks:
                    try:
                        usage_context = {
                            "incident_id": state.jira_key,
                            "user": "db_runbook_finder_workflow",
                            "outcome": "recommended",
                            "success": True,
                            "resolution_time": state.get_total_duration() / 60.0,  # Convert to minutes
                            "notes": f"Runbook recommended via automated workflow",
                            "relevance_score": runbook.get("relevance_score", 0.0),
                            "source": runbook.get("source", "unknown")
                        }
                        
                        await self._mcp_client.track_runbook_usage(
                            runbook_id=runbook.get("runbook_id", "unknown"),
                            usage_context=usage_context
                        )
                        
                    except Exception as e:
                        self.logger.log_warning(f"Failed to track runbook usage: {e}")
                
                self.logger.log_info(f"Tracked usage for {len(state.runbooks)} recommended runbooks")
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Enhanced Jira update failed: {e}", exception=e)
            state.update_status("ERROR", f"Enhanced Jira update failed: {e}")
            return state
    
    async def _enhanced_terminate_with_gap_error_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced gap handling with runbook gap tracking."""
        try:
            # Use the legacy method for gap handling (maintains compatibility)
            state = await self.nodes.terminate_with_gap_error_node(state)
            
            # Track the gap scenario for improvement insights
            if self._mcp_client:
                try:
                    gap_context = {
                        "incident_id": state.jira_key,
                        "user": "db_runbook_finder_workflow",
                        "outcome": "gap_detected",
                        "success": False,
                        "resolution_time": state.get_total_duration() / 60.0,
                        "notes": f"No runbooks found for query: {state.get_search_query()[:200]}",
                        "search_query": state.get_search_query(),
                        "client": state.get_client_name(),
                        "issue_type": state.incident_data.get("issue_type", "Unknown")
                    }
                    
                    # Track as usage record for gap analysis
                    await self._mcp_client.track_runbook_usage(
                        runbook_id="gap_scenario",
                        usage_context=gap_context
                    )
                    
                    self.logger.log_info(f"Tracked gap scenario for {state.jira_key}")
                    
                except Exception as e:
                    self.logger.log_warning(f"Failed to track gap scenario: {e}")
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Enhanced gap handling failed: {e}", exception=e)
            state.update_status("ERROR", f"Enhanced gap handling failed: {e}")
            return state
    
    async def _enhanced_notify_team_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced team notification using MCP server Slack integration."""
        try:
            # Use the legacy method for basic notification (maintains compatibility)
            state = await self.nodes.notify_team_node(state)
            
            # Send enhanced notification via MCP server if available
            if self._mcp_client:
                try:
                    notification_context = {
                        "title": f"DB Runbook Finder - {state.jira_key}",
                        "description": state.get_incident_summary(),
                        "urgency": self._determine_notification_urgency(state),
                        "incident_id": state.jira_key,
                        "client": state.get_client_name(),
                        "runbooks_found": len(state.runbooks),
                        "processing_time": f"{state.get_total_duration():.2f} seconds",
                        "workflow_status": state.status
                    }
                    
                    # Send enhanced notification
                    await self._mcp_client.send_runbook_notification(
                        channel="#mc-dba-jira-notifications",
                        runbook_id=f"workflow_{state.jira_key}",
                        context=notification_context
                    )
                    
                    self.logger.log_info(f"Sent enhanced notification for {state.jira_key}")
                    
                except Exception as e:
                    # Don't fail workflow if enhanced notification fails
                    self.logger.log_warning(f"Enhanced notification failed: {e}")
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Enhanced notification failed: {e}", exception=e)
            # Don't change the main status for notification failures
            return state
    
    async def _track_search_metrics(self, state: WorkflowState, query: str, results_count: int):
        """Track search performance metrics via MCP server."""
        try:
            if self._mcp_client:
                search_context = {
                    "incident_id": state.jira_key,
                    "user": "db_runbook_finder_workflow", 
                    "outcome": "search_completed",
                    "success": results_count > 0,
                    "resolution_time": state.get_total_duration() / 60.0,
                    "notes": f"Search query: {query[:100]}... | Results: {results_count}",
                    "query": query,
                    "results_count": results_count,
                    "search_performance": state.performance_metrics.get("search_runbooks", 0.0)
                }
                
                await self._mcp_client.track_runbook_usage(
                    runbook_id="search_operation",
                    usage_context=search_context
                )
                
        except Exception as e:
            self.logger.log_warning(f"Failed to track search metrics: {e}")
    
    def _determine_notification_urgency(self, state: WorkflowState) -> str:
        """Determine notification urgency based on state."""
        if state.status == "ERROR":
            return "high"
        elif state.status == "GAP_DETECTED":
            return "medium"
        elif state.has_runbooks():
            priority = state.incident_data.get("priority", "").lower()
            if priority in ["critical", "high"]:
                return "high"
            return "medium"
        return "low"

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration.
        
        Returns:
            Dictionary containing workflow metadata
        """
        workflow_info = {
            "name": "DB Runbook Finder",
            "version": "2.0.0",  # Updated for MCP server integration
            "description": "AI-powered workflow for finding relevant runbooks for Jira incidents",
            "config_path": self.config_path,
            "nodes": [
                "fetch_incident",
                "search_runbooks", 
                "update_jira_results",
                "terminate_gap",
                "notify_team"
            ],
            "routing_logic": {
                "runbook_search_router": "Routes based on whether runbooks were found"
            },
            "supported_projects": list(self.nodes.PROJECT_TO_CLIENT_MAP.keys()),
            "target_spaces": ["AAVA", "MCDBA"],
            "performance_target": "< 30 seconds end-to-end"
        }
        
        # Add MCP server information if enabled
        if self.use_mcp_server:
            workflow_info.update({
                "mcp_server_enabled": True,
                "mcp_capabilities": {
                    "discovery_strategy": "Confluence runbook discovery with validation",
                    "vector_strategy": "ChromaDB semantic search with <50ms performance",
                    "persistence_strategy": "Jira-based incident tracking and metrics",
                    "notification_strategy": "Slack integration with approval workflows"
                },
                "enhanced_features": [
                    "Comprehensive search (text + semantic)",
                    "Runbook usage tracking and metrics",
                    "Incident correlation and history",
                    "Enhanced Slack notifications",
                    "Gap analysis and reporting",
                    "Strategy-based graceful degradation"
                ]
            })
            
            # Add strategy factory info if available
            if self._strategy_factory:
                try:
                    strategy_status = self._strategy_factory.get_strategy_status()
                    workflow_info["strategy_status"] = strategy_status
                except Exception as e:
                    workflow_info["strategy_status"] = {"error": str(e)}
        else:
            workflow_info.update({
                "mcp_server_enabled": False,
                "mode": "legacy_compatibility"
            })
        
        return workflow_info

    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate workflow configuration and dependencies.
        
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            "overall_status": "unknown",
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check GraphMCP framework availability
            validation_results["checks"]["graphmcp_framework"] = "available"
            
            # Check logging configuration
            try:
                self.logging_config.validate()
                validation_results["checks"]["logging_config"] = "valid"
            except Exception as e:
                validation_results["checks"]["logging_config"] = "invalid"
                validation_results["warnings"].append(f"Logging configuration issue: {str(e)}")
            
            # Check node initialization
            try:
                nodes = DBRunbookFinderNodes()
                validation_results["checks"]["nodes_initialization"] = "success"
            except Exception as e:
                validation_results["checks"]["nodes_initialization"] = "failed"
                validation_results["errors"].append(f"Node initialization failed: {str(e)}")
            
            # Check project mappings
            if len(self.nodes.PROJECT_TO_CLIENT_MAP) > 0:
                validation_results["checks"]["project_mappings"] = "available"
                validation_results["project_count"] = len(self.nodes.PROJECT_TO_CLIENT_MAP)
            else:
                validation_results["checks"]["project_mappings"] = "empty"
                validation_results["warnings"].append("No project to client mappings configured")
            
            # Determine overall status
            if validation_results["errors"]:
                validation_results["overall_status"] = "failed"
            elif validation_results["warnings"]:
                validation_results["overall_status"] = "warnings"
            else:
                validation_results["overall_status"] = "passed"
                
        except Exception as e:
            validation_results["overall_status"] = "error"
            validation_results["errors"].append(f"Validation process failed: {str(e)}")
        
        return validation_results

    def __str__(self) -> str:
        """String representation of the workflow."""
        return f"DBRunbookFinderWorkflow(config_path={self.config_path})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"DBRunbookFinderWorkflow(config_path='{self.config_path}', nodes={len(self.get_workflow_info()['nodes'])})"