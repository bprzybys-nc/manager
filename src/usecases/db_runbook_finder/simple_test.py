#!/usr/bin/env python3
"""
Simple test script for DB Runbook Finder workflow.
"""

import asyncio
import sys
from state import WorkflowState
from nodes import DBRunbookFinderNodes

async def simple_workflow_test():
    """Test the workflow without complex logging to avoid JSON serialization issues."""
    print("🔄 Testing DB Runbook Finder Workflow")
    print("=" * 50)
    
    # Initialize nodes
    nodes = DBRunbookFinderNodes()
    
    # Test with AGENT-6 ticket
    state = WorkflowState(jira_key="AGENT-6")
    print(f"Initial state: {state.jira_key}")
    
    # Step 1: Fetch incident
    print("\n📋 Step 1: Fetching incident data...")
    state = await nodes.fetch_incident_node(state)
    print(f"   Client: {state.get_client_name()}")
    print(f"   Summary: {state.get_incident_summary()}")
    
    # Step 2: Search runbooks
    print("\n🔍 Step 2: Searching for runbooks...")
    state = await nodes.search_runbooks_node(state)
    print(f"   Found {len(state.runbooks)} runbooks")
    
    # Step 3: Process results
    if state.has_runbooks():
        print("\n✅ Step 3: Updating Jira with results...")
        state = await nodes.update_jira_with_results_node(state)
    else:
        print("\n⚠️ Step 3: Handling gap scenario...")
        state = await nodes.terminate_with_gap_error_node(state)
    
    # Step 4: Notify team
    print("\n📢 Step 4: Sending team notification...")
    state = await nodes.notify_team_node(state)
    
    # Summary
    print(f"\n🎯 Final Results:")
    print(f"   Status: {state.status}")
    print(f"   Client: {state.get_client_name()}")
    print(f"   Duration: {state.get_total_duration():.2f}s")
    print(f"   Runbooks: {len(state.runbooks)}")
    
    if state.runbooks:
        print(f"\n📚 Top Runbooks:")
        for i, rb in enumerate(state.runbooks[:3], 1):
            print(f"   {i}. {rb['title']} ({rb['relevance_score']:.1%})")
    
    return state

if __name__ == "__main__":
    result = asyncio.run(simple_workflow_test())
    sys.exit(0 if result.is_completed() else 1)