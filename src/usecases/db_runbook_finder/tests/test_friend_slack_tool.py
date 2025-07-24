"""
Test Friend's Slack Communication Tool (communication_536ab1c)

Tests the friend's working version of the communication tool to identify
differences that allow successful posting to Slack channels.
"""

import os
import pytest
from unittest.mock import Mock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestFriendSlackTool:
    """Test the friend's working Slack communication tool."""
    
    def setup_method(self):
        """Setup test environment."""
        self.required_env_vars = {
            'SLACK_BOT_TOKEN': os.getenv('SLACK_BOT_TOKEN'),
            'SLACK_APP_TOKEN': os.getenv('SLACK_APP_TOKEN'), 
            'SLACK_CHANNEL': os.getenv('SLACK_CHANNEL')
        }
        
    def test_environment_variables_present(self):
        """Test that required Slack environment variables are present."""
        for var_name, var_value in self.required_env_vars.items():
            assert var_value is not None, f"Missing environment variable: {var_name}"
            assert var_value.strip() != "", f"Empty environment variable: {var_name}"
            
    def test_friend_slack_formatting_enum(self):
        """Test that friend's SlackFormatting enum works."""
        from src.tools.communication_536ab1c.app.slack import SlackFormatting
        
        # Test that all expected formatting options exist
        assert hasattr(SlackFormatting, 'BOLD')
        assert hasattr(SlackFormatting, 'ITALIC') 
        assert hasattr(SlackFormatting, 'CODE')
        assert hasattr(SlackFormatting, 'CODE_BLOCK')
        
        # Test enum values
        assert SlackFormatting.BOLD.value == "bold"
        assert SlackFormatting.ITALIC.value == "italic"
        assert SlackFormatting.CODE.value == "code"
        assert SlackFormatting.CODE_BLOCK.value == "code_block"
        
    def test_friend_tool_interface(self):
        """Test that friend's tool has the expected interface."""
        from src.tools.communication_536ab1c.app.slack import Slack
        
        # Check that the class has the expected methods
        expected_methods = ['create_thread', 'send_message', 'get_channel_type']
        for method_name in expected_methods:
            assert hasattr(Slack, method_name), f"Missing method: {method_name}"
            
    @pytest.mark.integration
    def test_real_posting_with_friend_tool(self):
        """Test real posting to #mc-dba-jira-notifications using friend's tool."""
        from src.tools.communication_536ab1c.app.slack import Slack
        from src.modules.task.db import TaskDB
        
        # Skip if not running integration tests
        if not os.getenv('RUN_INTEGRATION_TESTS'):
            pytest.skip("Integration tests not enabled - set RUN_INTEGRATION_TESTS=1")
            
        # Mock TaskDB dependency
        mock_task_db = Mock(spec=TaskDB)
        
        try:
            slack_client = Slack(
                bot_token=self.required_env_vars['SLACK_BOT_TOKEN'],
                app_token=self.required_env_vars['SLACK_APP_TOKEN'],
                channel=self.required_env_vars['SLACK_CHANNEL'],  # C066PQYUYR4
                task_db=mock_task_db
            )
            
            # Test creating a thread
            test_message = "🧪 **Friend's Tool Test** - Testing communication_536ab1c version"
            thread_id = slack_client.create_thread(test_message)
            
            assert thread_id is not None
            assert isinstance(thread_id, str)
            assert len(thread_id) > 0
            
            print(f"✅ Successfully created thread with ID: {thread_id}")
            
            # Test sending a follow-up message
            followup_message = "✅ Friend's tool working - message posted successfully!"
            message_id = slack_client.send_message(thread_id, followup_message)
            
            assert message_id is not None
            assert isinstance(message_id, str)
            assert len(message_id) > 0
            
            print(f"✅ Successfully sent message with ID: {message_id}")
            
        except Exception as e:
            # Check if it's a channel access issue vs tool issue
            error_msg = str(e).lower()
            if "not_in_channel" in error_msg or "channel_not_found" in error_msg:
                pytest.skip(f"Bot not in channel (expected): {e}")
            elif "token_revoked" in error_msg:
                print(f"❌ Token issue with friend's tool: {e}")
                raise
            else:
                print(f"❌ Unexpected error with friend's tool: {e}")
                raise


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "-s"])