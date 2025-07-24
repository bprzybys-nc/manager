#!/usr/bin/env python3
"""
DB Runbook Finder Demo Script

This script runs the complete DB Runbook Finder workflow with real integrations.
Perfect for demos and testing with any Jira ticket ID.
"""

import sys
import asyncio
from dotenv import load_dotenv

# Load environment and setup path
load_dotenv()
sys.path.insert(0, 'src')

from usecases.db_runbook_finder.workflow import DBRunbookFinderWorkflow

async def main():
    print("🚀 DB Runbook Finder - Production Demo")
    print("=" * 50)
    print("🎯 Features:")
    print("  ✅ Real Jira API integration")
    print("  ✅ ChromaDB vector search (16 runbooks)")
    print("  ✅ Real Slack notifications")
    print("  ✅ Rich progress displays")
    print("=" * 50)
    print()
    
    # Get ticket ID from user
    ticket = input("🎫 Enter Jira ticket ID (or press Enter for AGENT-13): ").strip()
    if not ticket:
        ticket = "AGENT-13"
        print(f"📋 Using default ticket: {ticket}")
    
    print()
    print(f"🚀 Starting workflow for {ticket}...")
    print("=" * 50)
    
    try:
        # Run the complete workflow with real integrations
        workflow = DBRunbookFinderWorkflow(use_real_tools=True)
        result = await workflow.run(ticket)
        
        print("=" * 50)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print(f"   Status: {result.status}")
        print(f"   Runbooks Found: {len(result.runbooks)}")
        print(f"   Total Time: {result.get_total_duration():.2f} seconds")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        print("💡 Make sure:")
        print("  - Jira credentials are set in .env")
        print("  - ChromaDB collection 'mcdb-runbooks' exists")
        print("  - Ticket ID exists in Jira")

if __name__ == "__main__":
    asyncio.run(main())