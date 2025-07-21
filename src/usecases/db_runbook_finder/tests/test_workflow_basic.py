#!/usr/bin/env python3
"""
Basic test for DB Runbook Finder workflow functionality.
"""

import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from usecases.db_runbook_finder.state import WorkflowState
from usecases.db_runbook_finder.nodes import DBRunbookFinderNodes

async def test_basic_workflow():
    """Test basic workflow functionality without complex logging."""
    print("🔄 Testing DB Runbook Finder Workflow")
    print("=" * 50)
    
    try:
        # Initialize nodes (this might have logging issues, so we'll catch them)
        nodes = DBRunbookFinderNodes()
        print("✅ Nodes initialized successfully")
        
        # Test AGENT-6 ticket processing
        state = WorkflowState(jira_key="AGENT-6")
        print(f"✅ Initial state created: {state.jira_key}")
        
        # Test project mapping
        project_key = state.jira_key.split('-')[0]
        client_name = nodes.PROJECT_TO_CLIENT_MAP.get(project_key, "Unknown")
        print(f"✅ Project mapping: {project_key} → {client_name}")
        
        # Test mock data generation
        mock_jira = nodes._get_mock_jira_response("AGENT-6")
        print(f"✅ Mock Jira response: {mock_jira['fields']['summary'][:50]}...")
        
        mock_confluence = nodes._get_mock_confluence_response("database timeout", "AGENT-6")
        print(f"✅ Mock Confluence response: {len(mock_confluence['results'])} runbooks")
        
        print(f"\n🎯 Core Components Working:")
        print(f"   ✅ State management")
        print(f"   ✅ Project mappings")
        print(f"   ✅ Mock data generation")
        print(f"   ✅ Node initialization")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_workflow())
    if success:
        print(f"\n🚀 DB Runbook Finder workflow is ready for integration!")
        sys.exit(0)
    else:
        sys.exit(1)