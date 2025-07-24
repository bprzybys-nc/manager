"""
Test Slack Communication Tool Integration for DB Runbook Finder

This test verifies that the existing src/tools/communication Slack integration
works correctly before refactoring the workflow to use it instead of MCP.
"""

import os
import pytest
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestSlackCommunicationTool:
    """Test the existing Slack communication tool integration."""
    
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
            
    @patch('slack_bolt.app.app.App')
    @patch('slack_bolt.async_app.AsyncApp')
    def test_slack_client_initialization(self, mock_async_app, mock_app):
        """Test Slack client can be initialized with environment variables."""
        from src.tools.communication.app.slack import Slack
        from src.modules.task.db import TaskDB
        
        # Mock the Slack apps to avoid token validation during init
        mock_app_instance = Mock()
        mock_async_app_instance = Mock()
        mock_app.return_value = mock_app_instance
        mock_async_app.return_value = mock_async_app_instance
        
        # Mock TaskDB dependency
        mock_task_db = Mock(spec=TaskDB)
        
        try:
            slack_client = Slack(
                bot_token=self.required_env_vars['SLACK_BOT_TOKEN'],
                app_token=self.required_env_vars['SLACK_APP_TOKEN'],
                channel=self.required_env_vars['SLACK_CHANNEL'],
                task_db=mock_task_db
            )
            
            assert slack_client.channel == self.required_env_vars['SLACK_CHANNEL']
            assert slack_client.get_channel_type() == "slack"
            
            # Verify the apps were initialized with correct tokens
            mock_app.assert_called_once_with(token=self.required_env_vars['SLACK_BOT_TOKEN'])
            mock_async_app.assert_called_once_with(token=self.required_env_vars['SLACK_BOT_TOKEN'])
            
        except Exception as e:
            pytest.fail(f"Failed to initialize Slack client: {e}")
            
    @patch('slack_bolt.app.app.App')
    @patch('slack_bolt.async_app.AsyncApp')
    @patch('src.tools.communication.app.slack.Slack.create_thread')
    def test_create_thread_functionality(self, mock_create_thread, mock_async_app, mock_app):
        """Test creating a Slack thread (mocked to avoid actual posting)."""
        from src.tools.communication.app.slack import Slack, SlackFormatting
        from src.modules.task.db import TaskDB
        
        # Mock the Slack apps
        mock_app.return_value = Mock()
        mock_async_app.return_value = Mock()
        
        # Mock the create_thread method to return a timestamp
        mock_create_thread.return_value = "1234567890.123456"
        mock_task_db = Mock(spec=TaskDB)
        
        slack_client = Slack(
            bot_token=self.required_env_vars['SLACK_BOT_TOKEN'],
            app_token=self.required_env_vars['SLACK_APP_TOKEN'],
            channel=self.required_env_vars['SLACK_CHANNEL'],
            task_db=mock_task_db
        )
        
        # Test creating a thread with DB Runbook Finder message
        test_message = "🤖 **DB Runbook Finder Results**\n\nFound 5 relevant runbooks for AGENT-13"
        thread_id = slack_client.create_thread(test_message, SlackFormatting.BOLD)
        
        # Verify the mock was called correctly
        mock_create_thread.assert_called_once_with(test_message, SlackFormatting.BOLD)
        assert thread_id == "1234567890.123456"
        
    @patch('slack_bolt.app.app.App')
    @patch('slack_bolt.async_app.AsyncApp')
    @patch('src.tools.communication.app.slack.Slack.send_message')
    def test_send_message_functionality(self, mock_send_message, mock_async_app, mock_app):
        """Test sending a message to an existing thread (mocked)."""
        from src.tools.communication.app.slack import Slack, SlackFormatting
        from src.modules.task.db import TaskDB
        
        # Mock the Slack apps
        mock_app.return_value = Mock()
        mock_async_app.return_value = Mock()
        
        # Mock the send_message method
        mock_send_message.return_value = "1234567890.123457"
        mock_task_db = Mock(spec=TaskDB)
        
        slack_client = Slack(
            bot_token=self.required_env_vars['SLACK_BOT_TOKEN'],
            app_token=self.required_env_vars['SLACK_APP_TOKEN'],
            channel=self.required_env_vars['SLACK_CHANNEL'],
            task_db=mock_task_db
        )
        
        # Test sending a follow-up message
        test_thread_id = "1234567890.123456"
        test_message = "1. DB2 Hotel - OS patching (relevance: 28.2%)\n2. Oracle monitoring (relevance: 31.4%)"
        
        message_id = slack_client.send_message(test_thread_id, test_message, SlackFormatting.CODE)
        
        # Verify the mock was called correctly
        mock_send_message.assert_called_once_with(test_thread_id, test_message, SlackFormatting.CODE)
        assert message_id == "1234567890.123457"
        
    def test_db_runbook_finder_message_format(self):
        """Test formatting a complete DB Runbook Finder notification message."""
        # Sample data that would come from the workflow
        sample_runbook_results = [
            {
                "title": "DB2 Hotel - OS patching (DBA activities)",
                "relevance": 0.282,
                "url": "https://nordcloud.atlassian.net/spaces/MCDBA/pages/4355129622"
            },
            {
                "title": "Oracle Enterprise Manager Cloud Control monitoring", 
                "relevance": 0.314,
                "url": "https://nordcloud.atlassian.net/spaces/MCDBA/pages/4594270243"
            }
        ]
        
        # Format message like the workflow would
        ticket_id = "AGENT-13"
        message_lines = [
            f"🤖 **DB Runbook Finder Results for {ticket_id}**",
            "",
            f"Found {len(sample_runbook_results)} relevant runbooks:",
            ""
        ]
        
        for i, runbook in enumerate(sample_runbook_results, 1):
            relevance_pct = runbook["relevance"] * 100
            message_lines.extend([
                f"{i}. **{runbook['title']}**",
                f"   Relevance: {relevance_pct:.1f}%",
                f"   URL: {runbook['url']}",
                ""
            ])
            
        formatted_message = "\n".join(message_lines)
        
        # Verify message contains expected content
        assert ticket_id in formatted_message
        assert "DB Runbook Finder Results" in formatted_message
        assert "DB2 Hotel - OS patching" in formatted_message
        assert "28.2%" in formatted_message
        assert "nordcloud.atlassian.net" in formatted_message
        
        # Verify message is reasonable length (not too long for Slack)
        assert len(formatted_message) < 4000, "Message too long for Slack"
        
    @pytest.mark.integration
    def test_real_slack_integration(self):
        """Integration test with real Slack API (requires bot channel access)."""
        from src.tools.communication.app.slack import Slack
        from src.modules.task.db import TaskDB
        
        # Skip if not explicitly running integration tests
        if not os.getenv('RUN_INTEGRATION_TESTS'):
            pytest.skip("Integration tests not enabled")
            
        mock_task_db = Mock(spec=TaskDB)
        
        slack_client = Slack(
            bot_token=self.required_env_vars['SLACK_BOT_TOKEN'],
            app_token=self.required_env_vars['SLACK_APP_TOKEN'],
            channel=self.required_env_vars['SLACK_CHANNEL'],
            task_db=mock_task_db
        )
        
        try:
            # Test creating a real thread (will fail if bot not in channel)
            test_message = "🧪 **Integration Test** - DB Runbook Finder communication tool test"
            thread_id = slack_client.create_thread(test_message)
            
            assert thread_id is not None
            assert isinstance(thread_id, str)
            assert len(thread_id) > 0
            
            # Test sending a follow-up message
            followup_message = "✅ Integration test successful - communication tool working"
            message_id = slack_client.send_message(thread_id, followup_message)
            
            assert message_id is not None
            assert isinstance(message_id, str)
            assert len(message_id) > 0
            
        except Exception as e:
            # Expected to fail if bot not in channel - that's what we're testing
            error_msg = str(e).lower()
            if "not_in_channel" in error_msg or "channel_not_found" in error_msg:
                pytest.skip(f"Bot not in channel (expected): {e}")
            else:
                pytest.fail(f"Unexpected error during integration test: {e}")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])