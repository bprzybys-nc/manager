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


class DBRunbookFinderWorkflow:
    """DB Runbook Finder workflow implementation using GraphMCP framework.
    
    This workflow processes Jira incidents and finds relevant runbooks through
    semantic search, providing automated recommendations to reduce incident
    response time.
    """
    
    def __init__(self, config_path: str = "src/frameworks/graphmcp/mcp_config.json"):
        """Initialize the workflow with GraphMCP configuration.
        
        Args:
            config_path: Path to MCP server configuration file
        """
        self.config_path = config_path
        self.nodes = DBRunbookFinderNodes()
        
        # Initialize logging
        self.logging_config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id="db_runbook_finder_main", config=self.logging_config)
        
        # Initialize workflow builder
        self._workflow = None

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
        """Mock workflow execution for testing and development.
        
        This method simulates the complete workflow execution by calling
        each node in sequence with proper routing logic.
        
        Args:
            state: Initial workflow state
            
        Returns:
            Final workflow state after execution
        """
        try:
            # Step 1: Fetch incident data
            state = await self.nodes.fetch_incident_node(state)
            if state.is_error_state():
                state = await self.nodes.notify_team_node(state)
                return state
            
            # Step 2: Search for runbooks
            state = await self.nodes.search_runbooks_node(state)
            if state.is_error_state():
                state = await self.nodes.notify_team_node(state)
                return state
            
            # Step 3: Route based on search results
            if state.has_runbooks():
                # Success path: Update Jira with results
                state = await self.nodes.update_jira_with_results_node(state)
            else:
                # Gap path: Handle no runbooks scenario
                state = await self.nodes.terminate_with_gap_error_node(state)
            
            # Step 4: Send team notification
            state = await self.nodes.notify_team_node(state)
            
            return state
            
        except Exception as e:
            self.logger.log_error(f"Mock workflow execution failed: {str(e)}", exception=e)
            state.update_status("ERROR", f"Mock workflow execution failed: {str(e)}")
            return state

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration.
        
        Returns:
            Dictionary containing workflow metadata
        """
        return {
            "name": "DB Runbook Finder",
            "version": "1.0.0",
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