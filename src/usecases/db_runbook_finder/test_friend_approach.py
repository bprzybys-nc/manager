#!/usr/bin/env python3
"""
Test Friend's Direct Slack Integration Approach

Uses the friend's communication tool version (communication_536ab1c) 
to test direct posting to #mc-dba-jira-notifications without MCP.
"""

import os
import sys
import asyncio
from unittest.mock import Mock
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Load environment variables - force override system env vars
load_dotenv(override=True)

def test_friend_slack_direct():
    """Test friend's direct Slack integration approach."""
    
    print("🧪 Testing friend's direct Slack integration approach...")
    
    # Import friend's Slack tool
    try:
        from src.tools.communication_536ab1c.app.slack import Slack, SlackFormatting
        from src.modules.task.db import TaskDB
    except ImportError:
        # Try alternative import path  
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        sys.path.insert(0, project_root)
        from src.tools.communication_536ab1c.app.slack import Slack, SlackFormatting
        from src.modules.task.db import TaskDB
    
    # Environment variables (using friend's approach - no SLACK_TEAM_ID)
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    app_token = os.getenv('SLACK_APP_TOKEN') 
    channel = os.getenv('SLACK_CHANNEL')  # C066PQYUYR4
    
    print(f"📋 Environment variables:")
    print(f"   SLACK_BOT_TOKEN: {bot_token}")
    print(f"   SLACK_APP_TOKEN: {app_token}")
    print(f"   SLACK_CHANNEL: {channel}")
    print(f"   SLACK_TEAM_ID: Not used (friend's approach)")
    
    if not all([bot_token, app_token, channel]):
        print("❌ Missing required environment variables")
        return False
        
    # Mock TaskDB dependency 
    mock_task_db = Mock(spec=TaskDB)
    
    try:
        print("\n🔧 Initializing friend's Slack client...")
        # Create event loop for async components
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        slack_client = Slack(
            bot_token=bot_token,
            app_token=app_token,
            channel=channel,
            task_db=mock_task_db
        )
        
        print("✅ Slack client initialized successfully")
        
        # Test creating a thread
        print("\n📝 Creating thread in #mc-dba-jira-notifications...")
        test_message = "🧪 **Friend's Tool Test** - DB Runbook Finder using communication_536ab1c"
        
        thread_id = slack_client.create_thread(test_message)
        print(f"✅ Thread created successfully! Thread ID: {thread_id}")
        
        # Test sending a follow-up message
        print("\n💬 Sending follow-up message...")
        followup_message = """✅ **Success!** Friend's communication tool working perfectly!

📋 **Test Results:**
• Thread creation: ✅ Working
• Message posting: ✅ Working  
• Channel: #mc-dba-jira-notifications
• Tool version: communication_536ab1c

🎯 **Next steps:** Refactor DB Runbook Finder to use this working approach"""
        
        message_id = slack_client.send_message(thread_id, followup_message, SlackFormatting.BOLD)
        print(f"✅ Follow-up message sent successfully! Message ID: {message_id}")
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "not_in_channel" in error_msg or "channel_not_found" in error_msg:
            print(f"⚠️  Bot not in channel (expected): {e}")
            print("   This is a permission issue, not a tool issue")
            return False
        elif "token_revoked" in error_msg:
            print(f"❌ Token revoked: {e}")
            return False
        else:
            print(f"❌ Unexpected error: {e}")
            raise

def main():
    """Main test function."""
    print("🚀 Testing Friend's Direct Slack Communication Approach")
    print("=" * 60)
    
    success = test_friend_slack_direct()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Friend's approach works! Ready for refactoring.")
    else:
        print("❌ FAILED: Need to investigate further.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)