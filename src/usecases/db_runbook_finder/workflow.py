"""
DB Runbook Finder Workflow

Main workflow class that orchestrates the AI-powered runbook discovery process
using the GraphMCP framework and LangGraph state management.
"""

from typing import Dict, Any
from frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

from .state import WorkflowState
from .nodes import DBRunbookFinderNodes


class DBRunbookFinderWorkflow:
    """DB Runbook Finder workflow implementation using GraphMCP framework.
    
    This workflow processes Jira incidents and finds relevant runbooks through
    semantic search, providing automated recommendations to reduce incident
    response time.
    """
    
    def __init__(self, config_path: str = "src/frameworks/graphmcp/clients/mcp_config.json", use_real_tools: bool = False):
        """Initialize the workflow with direct node execution.
        
        Args:
            config_path: Path to MCP configuration file for GraphMCP client initialization
            use_real_tools: Whether to use real tool integrations when available
        """
        self.config_path = config_path
        self.use_real_tools = use_real_tools
        self.nodes = DBRunbookFinderNodes(config_path=config_path, use_real_tools=use_real_tools)
        
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

    async def run(self, jira_key: str) -> WorkflowState:
        """Execute DB Runbook Finder workflow with direct node execution."""
        self.logger.log_workflow_start({"jira_key": jira_key}, {"log_level": "INFO", "workflow": "db_runbook_finder"})
        
        state = WorkflowState(jira_key=jira_key)
        
        try:
            # Direct sequential execution
            state = await self.nodes.fetch_incident_node(state)
            if not state.is_error_state():
                state = await self.nodes.search_runbooks_node(state)
                
                # Router logic unchanged
                if state.has_runbooks():
                    state = await self.nodes.update_jira_with_results_node(state)
                else:
                    state = await self.nodes.terminate_with_gap_error_node(state)
                    
                state = await self.nodes.notify_team_node(state)
            
            self.logger.log_workflow_end(state.status, state.get_total_duration())
            return state
            
        except Exception as e:
            error_message = f"Workflow execution failed: {str(e)}"
            self.logger.log_error(error_message, exception=e)
            state.update_status("ERROR", error_message)
            return state

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration.
        
        Returns:
            Dictionary containing workflow metadata
        """
        workflow_info = {
            "name": "DB Runbook Finder",
            "version": "3.0.0",  # Updated for direct execution
            "description": "AI-powered workflow for finding relevant runbooks for Jira incidents",
            "execution_mode": "direct",
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
            "performance_target": "< 5 seconds per test execution"
        }
        
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
                DBRunbookFinderNodes(config_path=self.config_path, use_real_tools=self.use_real_tools)
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
        return "DBRunbookFinderWorkflow(execution_mode=direct)"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"DBRunbookFinderWorkflow(execution_mode=direct, nodes={len(self.get_workflow_info()['nodes'])})"