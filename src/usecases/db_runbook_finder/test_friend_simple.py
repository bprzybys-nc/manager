#!/usr/bin/env python3
"""
Simple Test for Friend's Slack Integration

Tests just the sync methods to avoid async complexity.
"""

import os
import sys
from unittest.mock import Mock
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Load environment variables - force override system env vars
load_dotenv(override=True)

def test_direct_slack_post():
    """Test direct Slack posting using curl to verify tokens work."""
    
    print("🧪 Testing direct Slack API calls...")
    
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    channel = os.getenv('SLACK_CHANNEL')
    
    print(f"📋 Using tokens from .env:")
    print(f"   SLACK_BOT_TOKEN: {bot_token}")
    print(f"   SLACK_CHANNEL: {channel}")
    
    if not all([bot_token, channel]):
        print("❌ Missing required environment variables")
        return False
        
    # Test with curl - simpler than dealing with async issues
    import subprocess
    
    try:
        print("\n📞 Testing auth with Slack API...")
        
        # Test auth.test
        auth_cmd = [
            'curl', '-X', 'POST',
            'https://slack.com/api/auth.test',
            '-H', f'Authorization: Bearer {bot_token}',
            '-H', 'Content-Type: application/json'
        ]
        
        result = subprocess.run(auth_cmd, capture_output=True, text=True, timeout=10)
        print(f"Auth test response: {result.stdout}")
        
        if '"ok":true' in result.stdout:
            print("✅ Token authentication successful!")
            
            # Test posting a message
            print("\n💬 Testing message posting...")
            
            message_data = {
                "channel": channel,
                "text": "🧪 **Friend's Tool Test** - Direct API call successful!\n\n✅ Using communication_536ab1c approach\n📋 No MCP, no SLACK_TEAM_ID required\n🎯 Ready for workflow integration"
            }
            
            import json
            
            post_cmd = [
                'curl', '-X', 'POST',
                'https://slack.com/api/chat.postMessage',
                '-H', f'Authorization: Bearer {bot_token}',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(message_data)
            ]
            
            post_result = subprocess.run(post_cmd, capture_output=True, text=True, timeout=10)
            print(f"Post message response: {post_result.stdout}")
            
            if '"ok":true' in post_result.stdout:
                print("✅ Message posted successfully!")
                return True
            else:
                print("❌ Message posting failed")
                return False
                
        else:
            print("❌ Token authentication failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing Friend's Direct Slack Approach (Simple)")
    print("=" * 60)
    
    success = test_direct_slack_post()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Friend's direct approach works!")
        print("💡 Key insights:")
        print("   • No SLACK_TEAM_ID required")
        print("   • Direct API calls work") 
        print("   • Ready to refactor workflow")
    else:
        print("❌ FAILED: Direct API approach not working")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)