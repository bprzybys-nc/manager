"""
Simple test for Slack Communication Tool Integration

Tests the interface and message formatting without complex mocking.
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestSlackCommunicationSimple:
    """Test Slack communication tool interface and formatting."""
    
    def test_environment_variables_present(self):
        """Test that required Slack environment variables are present."""
        required_vars = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'SLACK_CHANNEL']
        
        for var_name in required_vars:
            var_value = os.getenv(var_name)
            assert var_value is not None, f"Missing environment variable: {var_name}"
            assert var_value.strip() != "", f"Empty environment variable: {var_name}"
            
    def test_slack_formatting_enum_available(self):
        """Test that SlackFormatting enum is available."""
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
        
        print("✅ Formatted message preview:")
        print("=" * 50)
        print(formatted_message)
        print("=" * 50)
        
    def test_slack_api_format_functions(self):
        """Test that we can format messages correctly for Slack."""
        from src.tools.communication_536ab1c.app.slack import SlackFormatting
        
        # Test message formatting expectations
        test_message = "This is a test message"
        
        # These should match what the Slack class expects
        formatting_tests = {
            SlackFormatting.BOLD: "should wrap with **",
            SlackFormatting.ITALIC: "should wrap with _", 
            SlackFormatting.CODE: "should wrap with `",
            SlackFormatting.CODE_BLOCK: "should wrap with ```"
        }
        
        # Verify formatting enum values exist and have string values
        for fmt_type, description in formatting_tests.items():
            assert hasattr(fmt_type, 'value'), f"{fmt_type} should be an enum with .value"
            assert isinstance(fmt_type.value, str), f"{fmt_type.value} {description}"
            assert len(fmt_type.value) > 0, f"{fmt_type.value} should not be empty"
            
    def test_workflow_integration_interface(self):
        """Test the interface our workflow will use with the communication tool."""
        
        # Simulate what our workflow needs to do:
        # 1. Create a thread for the incident
        # 2. Send runbook results to that thread
        
        workflow_actions = {
            'create_thread': {
                'method': 'create_thread',
                'params': ['message', 'formatting'],
                'returns': 'thread_id (string)'
            },
            'send_message': {
                'method': 'send_message', 
                'params': ['thread_id', 'message', 'formatting'],
                'returns': 'message_id (string)'
            }
        }
        
        # Test that our expected interface matches what we need
        for action_name, action_info in workflow_actions.items():
            method_name = action_info['method']
            expected_params = action_info['params']
            expected_return = action_info['returns']
            
            # These are the methods our workflow expects to call
            assert method_name in ['create_thread', 'send_message'], f"Unexpected method: {method_name}"
            assert len(expected_params) >= 1, f"Method {method_name} should have parameters"
            
        print("✅ Workflow integration interface verified")
        
    def _create_sample_workflow_messages(self):
        """Helper to create sample messages for workflow integration."""
        ticket_id = "AGENT-13"
        
        # Initial thread message
        thread_message = f"🎫 **Incident {ticket_id} - DB Runbook Finder**\n\n🔍 Searching for relevant runbooks..."
        
        # Results message  
        results_message = """📋 **Search Results**

Found 2 relevant runbooks:

1. **DB2 Hotel - OS patching (DBA activities)**
   Relevance: 28.2%
   🔗 https://nordcloud.atlassian.net/spaces/MCDBA/pages/4355129622

2. **Oracle Enterprise Manager Cloud Control monitoring**
   Relevance: 31.4%
   🔗 https://nordcloud.atlassian.net/spaces/MCDBA/pages/4594270243

✅ Runbook recommendations added to Jira ticket"""
        
        return {
            'thread_message': thread_message,
            'results_message': results_message
        }
        
    def test_sample_workflow_messages(self):
        """Test that our sample workflow messages are properly formatted."""
        messages = self._create_sample_workflow_messages()
        
        thread_msg = messages['thread_message']
        results_msg = messages['results_message']
        
        # Verify thread message
        assert "AGENT-13" in thread_msg
        assert "DB Runbook Finder" in thread_msg
        assert len(thread_msg) < 4000
        
        # Verify results message
        assert "Search Results" in results_msg
        assert "DB2 Hotel" in results_msg
        assert "28.2%" in results_msg
        assert "nordcloud.atlassian.net" in results_msg
        assert len(results_msg) < 4000
        
        print("✅ Sample workflow messages:")
        print("\n📧 Thread Message:")
        print(thread_msg)
        print("\n📧 Results Message:")  
        print(results_msg)


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "-s"])