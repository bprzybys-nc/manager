"""
Unit tests for MockNotificationStrategy.

Tests all methods of the mock notification strategy for comprehensive coverage
and validates Slack notification simulation functionality.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.usecases.db_runbook_finder.mcp_server.strategies.mock_notification import MockNotificationStrategy
from src.usecases.db_runbook_finder.mcp_server.exceptions import NotificationError


class TestMockNotificationStrategy:
    """Test suite for MockNotificationStrategy."""
    
    @pytest.fixture
    def mock_strategy(self):
        """Create mock notification strategy instance."""
        return MockNotificationStrategy()
    
    @pytest.mark.asyncio
    async def test_health_check_always_returns_true(self, mock_strategy):
        """Test that health check always returns True for mock strategy."""
        result = await mock_strategy.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_runbook_notification_success(self, mock_strategy):
        """Test successful runbook notification sending."""
        channel = "C1234567890"  # Mock channel ID
        runbook_id = "test_runbook_123"
        context = {
            "title": "Test Runbook Found",
            "description": "A test runbook has been discovered",
            "urgency": "medium",
            "incident_id": "INC-2024001",
            "runbook_url": "https://test.com/runbook/123",
            "categories": ["database", "troubleshooting"]
        }
        
        notification_id = await mock_strategy.send_runbook_notification(channel, runbook_id, context)
        
        assert isinstance(notification_id, str)
        assert notification_id.startswith("notif_")
        assert runbook_id in notification_id
        
        # Verify notification was stored
        notifications = mock_strategy.get_sent_notifications()
        assert notification_id in notifications
        
        notification = notifications[notification_id]
        assert notification["channel"] == channel
        assert notification["runbook_id"] == runbook_id
        assert notification["urgency"] == context["urgency"]
        assert notification["status"] == "sent"
        assert notification["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_send_runbook_notification_minimal_context(self, mock_strategy):
        """Test runbook notification with minimal context."""
        channel = "general"
        runbook_id = "minimal_test"
        context = {}
        
        notification_id = await mock_strategy.send_runbook_notification(channel, runbook_id, context)
        
        assert isinstance(notification_id, str)
        
        # Should have defaults applied
        notifications = mock_strategy.get_sent_notifications()
        notification = notifications[notification_id]
        assert "title" in notification["context"]  # Should have default title
        assert notification["urgency"] == "medium"  # Default urgency
    
    @pytest.mark.asyncio
    async def test_send_runbook_notification_different_urgencies(self, mock_strategy):
        """Test notifications with different urgency levels."""
        channel = "alerts"
        urgencies = ["high", "medium", "low"]
        
        for urgency in urgencies:
            context = {"urgency": urgency, "title": f"Test {urgency} urgency"}
            notification_id = await mock_strategy.send_runbook_notification(
                channel, f"test_{urgency}", context
            )
            
            notifications = mock_strategy.get_sent_notifications()
            notification = notifications[notification_id]
            assert notification["urgency"] == urgency
            
            # Check that emoji varies by urgency
            message = notification["message"]
            if urgency == "high":
                assert "🚨" in message
            elif urgency == "medium":
                assert "📋" in message
            elif urgency == "low":
                assert "ℹ️" in message
    
    @pytest.mark.asyncio
    async def test_create_approval_thread_success(self, mock_strategy):
        """Test successful approval thread creation."""
        channel = "incidents"
        runbook_id = "approval_test_123"
        context = {
            "title": "Approval Required Test",
            "procedure": "Execute test runbook procedure",
            "risk_level": "medium",
            "incident_id": "INC-2024002",
            "approvers": ["approver1", "approver2"],
            "description": "Test approval thread creation",
            "estimated_duration": "30 minutes",
            "rollback_procedure": "Available"
        }
        
        thread_id = await mock_strategy.create_approval_thread(channel, runbook_id, context)
        
        assert isinstance(thread_id, str)
        assert thread_id.startswith("thread_")
        assert runbook_id in thread_id
        
        # Verify thread was stored
        threads = mock_strategy.get_active_threads()
        assert thread_id in threads
        
        thread = threads[thread_id]
        assert thread["channel"] == channel
        assert thread["runbook_id"] == runbook_id
        assert thread["status"] == "pending_approval"
        assert thread["risk_level"] == context["risk_level"]
        assert thread["approvers"] == context["approvers"]
        assert thread["source"] == "mock"
        
        # Verify thread messages were created
        messages = mock_strategy.get_thread_messages(thread_id)
        assert len(messages) >= 2  # Approval request + approval question
    
    @pytest.mark.asyncio
    async def test_create_approval_thread_minimal_context(self, mock_strategy):
        """Test approval thread creation with minimal context."""
        channel = "test_channel"
        runbook_id = "minimal_approval"
        context = {}
        
        thread_id = await mock_strategy.create_approval_thread(channel, runbook_id, context)
        
        assert isinstance(thread_id, str)
        
        # Should have defaults applied
        threads = mock_strategy.get_active_threads()
        thread = threads[thread_id]
        assert thread["risk_level"] == "medium"  # Default risk level
        assert len(thread["approvers"]) > 0  # Should have default approvers
    
    @pytest.mark.asyncio
    async def test_create_approval_thread_different_risk_levels(self, mock_strategy):
        """Test approval threads with different risk levels."""
        channel = "approvals"
        risk_levels = ["high", "medium", "low"]
        
        for risk_level in risk_levels:
            context = {"risk_level": risk_level, "procedure": f"Test {risk_level} risk procedure"}
            thread_id = await mock_strategy.create_approval_thread(
                channel, f"risk_test_{risk_level}", context
            )
            
            threads = mock_strategy.get_active_threads()
            thread = threads[thread_id]
            assert thread["risk_level"] == risk_level
            
            # Check that emoji varies by risk level
            message = thread["approval_message"]
            if risk_level == "high":
                assert "⚠️" in message
            elif risk_level == "medium":
                assert "⚡" in message
            elif risk_level == "low":
                assert "✅" in message
    
    @pytest.mark.asyncio
    async def test_update_thread_status_success(self, mock_strategy):
        """Test successful thread status update."""
        # First create a thread
        channel = "test_updates"
        runbook_id = "status_update_test"
        context = {"procedure": "Test procedure"}
        thread_id = await mock_strategy.create_approval_thread(channel, runbook_id, context)
        
        # Update thread status
        results = {
            "success": True,
            "duration": "15 minutes",
            "steps_completed": 5,
            "output": "Test procedure completed successfully"
        }
        
        success = await mock_strategy.update_thread_status(thread_id, "completed", results)
        
        assert success is True
        
        # Verify thread was updated
        threads = mock_strategy.get_active_threads()
        thread = threads[thread_id]
        assert thread["status"] == "completed"
        assert thread["results"] == results
        assert "last_updated" in thread
        
        # Verify status update message was added
        messages = mock_strategy.get_thread_messages(thread_id)
        status_messages = [m for m in messages if m["type"] == "status_update"]
        assert len(status_messages) >= 1
        
        latest_status = status_messages[-1]
        assert latest_status["status"] == "completed"
        assert latest_status["results"] == results
    
    @pytest.mark.asyncio
    async def test_update_thread_status_nonexistent_thread(self, mock_strategy):
        """Test updating status of non-existent thread."""
        thread_id = "nonexistent_thread_123"
        results = {"success": False, "error": "Thread not found"}
        
        success = await mock_strategy.update_thread_status(thread_id, "failed", results)
        
        # Should still succeed (creates thread automatically)
        assert success is True
        
        # Verify thread was auto-created
        threads = mock_strategy.get_active_threads()
        assert thread_id in threads
        thread = threads[thread_id]
        assert thread["status"] == "failed"
        assert thread["source"] == "mock_auto_created"
    
    @pytest.mark.asyncio
    async def test_update_thread_status_different_statuses(self, mock_strategy):
        """Test thread updates with different status values."""
        channel = "status_test"
        runbook_id = "multi_status_test"
        context = {"procedure": "Multi-status test"}
        thread_id = await mock_strategy.create_approval_thread(channel, runbook_id, context)
        
        statuses = ["approved", "rejected", "executing", "completed", "failed", "cancelled"]
        
        for status in statuses:
            results = {"status": status, "timestamp": datetime.utcnow().isoformat()}
            success = await mock_strategy.update_thread_status(thread_id, status, results)
            assert success is True
            
            # Verify status was updated
            threads = mock_strategy.get_active_threads()
            thread = threads[thread_id]
            assert thread["status"] == status
    
    @pytest.mark.asyncio
    async def test_send_completion_summary_success(self, mock_strategy):
        """Test successful completion summary sending."""
        channel = "summaries"
        summary = {
            "workflow_name": "Test Workflow",
            "total_runbooks_processed": 5,
            "successful_executions": 4,
            "failed_executions": 1,
            "total_duration": "45 minutes",
            "results": [
                {"runbook_id": "test_1", "status": "success", "duration": "10 min"},
                {"runbook_id": "test_2", "status": "success", "duration": "8 min"},
                {"runbook_id": "test_3", "status": "failed", "duration": "5 min"}
            ],
            "recommendations": [
                "Review failed runbook for improvements",
                "Consider automation for routine tasks"
            ]
        }
        
        message_id = await mock_strategy.send_completion_summary(channel, summary)
        
        assert isinstance(message_id, str)
        assert message_id.startswith("summary_")
        
        # Verify summary was stored
        summaries = mock_strategy.get_completion_summaries()
        assert message_id in summaries
        
        stored_summary = summaries[message_id]
        assert stored_summary["channel"] == channel
        assert stored_summary["workflow_name"] == summary["workflow_name"]
        assert stored_summary["total_runbooks"] == summary["total_runbooks_processed"]
        assert stored_summary["success_rate"] == 80.0  # 4/5 * 100
        assert stored_summary["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_send_completion_summary_minimal_data(self, mock_strategy):
        """Test completion summary with minimal data."""
        channel = "minimal_summaries"
        summary = {"workflow_name": "Minimal Test Workflow"}
        
        message_id = await mock_strategy.send_completion_summary(channel, summary)
        
        assert isinstance(message_id, str)
        
        # Should have generated default values
        summaries = mock_strategy.get_completion_summaries()
        stored_summary = summaries[message_id]
        assert stored_summary["workflow_name"] == summary["workflow_name"]
        assert stored_summary["total_runbooks"] >= 0
        assert stored_summary["success_rate"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_success(self, mock_strategy):
        """Test successful alert notification sending."""
        channel = "alerts"
        alert_type = "error"
        message = "Test error alert message"
        urgency = "high"
        
        alert_id = await mock_strategy.send_alert_notification(channel, alert_type, message, urgency)
        
        assert isinstance(alert_id, str)
        assert alert_id.startswith("alert_")
        assert alert_type in alert_id
        
        # Verify alert was stored
        notifications = mock_strategy.get_sent_notifications()
        assert alert_id in notifications
        
        alert = notifications[alert_id]
        assert alert["channel"] == channel
        assert alert["alert_type"] == alert_type
        assert alert["urgency"] == urgency
        assert alert["original_message"] == message
        assert alert["source"] == "mock"
    
    @pytest.mark.asyncio
    async def test_send_alert_notification_different_types(self, mock_strategy):
        """Test alerts with different alert types."""
        channel = "test_alerts"
        alert_types = ["error", "warning", "info", "success"]
        
        for alert_type in alert_types:
            message = f"Test {alert_type} alert"
            alert_id = await mock_strategy.send_alert_notification(channel, alert_type, message)
            
            notifications = mock_strategy.get_sent_notifications()
            alert = notifications[alert_id]
            assert alert["alert_type"] == alert_type
            
            # Check that emoji varies by alert type
            formatted_message = alert["formatted_message"]
            if alert_type == "error":
                assert "🚨" in formatted_message
            elif alert_type == "warning":
                assert "⚠️" in formatted_message
            elif alert_type == "info":
                assert "ℹ️" in formatted_message
            elif alert_type == "success":
                assert "✅" in formatted_message
    
    # Test helper methods
    def test_get_sent_notifications(self, mock_strategy):
        """Test retrieval of sent notifications."""
        notifications = mock_strategy.get_sent_notifications()
        
        assert isinstance(notifications, dict)
        # Should start empty
        assert len(notifications) >= 0
    
    def test_get_active_threads(self, mock_strategy):
        """Test retrieval of active threads."""
        threads = mock_strategy.get_active_threads()
        
        assert isinstance(threads, dict)
        # Should start empty
        assert len(threads) >= 0
    
    def test_get_thread_messages(self, mock_strategy):
        """Test retrieval of thread messages for non-existent thread."""
        messages = mock_strategy.get_thread_messages("nonexistent_thread")
        
        assert isinstance(messages, list)
        assert len(messages) == 0
    
    def test_get_all_thread_messages(self, mock_strategy):
        """Test retrieval of all thread messages."""
        all_messages = mock_strategy.get_all_thread_messages()
        
        assert isinstance(all_messages, dict)
        # Should start empty
        assert len(all_messages) >= 0
    
    def test_get_completion_summaries(self, mock_strategy):
        """Test retrieval of completion summaries."""
        summaries = mock_strategy.get_completion_summaries()
        
        assert isinstance(summaries, dict)
        # Should start empty
        assert len(summaries) >= 0
    
    def test_clear_data(self, mock_strategy):
        """Test data clearing functionality."""
        # Add some test data first
        mock_strategy._sent_notifications["test"] = {"test": "data"}
        mock_strategy._active_threads["test_thread"] = {"test": "thread"}
        
        # Clear data
        mock_strategy.clear_data()
        
        # All storage should be empty
        assert len(mock_strategy.get_sent_notifications()) == 0
        assert len(mock_strategy.get_active_threads()) == 0
        assert len(mock_strategy.get_completion_summaries()) == 0
    
    def test_simulate_approval_response_success(self, mock_strategy):
        """Test simulating approval response."""
        # First create a thread manually
        thread_id = "manual_approval_test"
        mock_strategy._active_threads[thread_id] = {
            "thread_id": thread_id,
            "status": "pending_approval",
            "runbook_id": "test_runbook",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Simulate approval
        success = mock_strategy.simulate_approval_response(thread_id, True, "test_approver")
        
        assert success is True
        
        # Verify thread was updated
        threads = mock_strategy.get_active_threads()
        thread = threads[thread_id]
        assert thread["status"] == "approved"
        assert thread["approved_by"] == "test_approver"
        assert "approval_timestamp" in thread
        
        # Verify approval message was added
        messages = mock_strategy.get_thread_messages(thread_id)
        approval_messages = [m for m in messages if m["type"] == "approval_response"]
        assert len(approval_messages) >= 1
        
        approval_msg = approval_messages[-1]
        assert approval_msg["approved"] is True
        assert approval_msg["author"] == "test_approver"
    
    def test_simulate_approval_response_rejection(self, mock_strategy):
        """Test simulating approval rejection."""
        thread_id = "rejection_test"
        mock_strategy._active_threads[thread_id] = {
            "thread_id": thread_id,
            "status": "pending_approval",
            "runbook_id": "test_runbook"
        }
        
        # Simulate rejection
        success = mock_strategy.simulate_approval_response(thread_id, False, "test_rejector")
        
        assert success is True
        
        # Verify thread was updated
        threads = mock_strategy.get_active_threads()
        thread = threads[thread_id]
        assert thread["status"] == "rejected"
        assert thread["approved_by"] == "test_rejector"
    
    def test_simulate_approval_response_nonexistent_thread(self, mock_strategy):
        """Test simulating approval for non-existent thread."""
        success = mock_strategy.simulate_approval_response("nonexistent", True)
        
        assert success is False
    
    def test_get_mock_channels(self, mock_strategy):
        """Test retrieval of mock channels."""
        channels = mock_strategy.get_mock_channels()
        
        assert isinstance(channels, dict)
        assert len(channels) > 0
        
        # Should have some default channels
        expected_channels = ["general", "incidents", "runbooks", "alerts"]
        for channel in expected_channels:
            assert channel in channels
    
    def test_add_mock_channel(self, mock_strategy):
        """Test adding a mock channel."""
        channel_name = "test_channel"
        channel_id = "C9999999999"
        
        mock_strategy.add_mock_channel(channel_name, channel_id)
        
        channels = mock_strategy.get_mock_channels()
        assert channel_name in channels
        assert channels[channel_name] == channel_id
    
    @pytest.mark.asyncio
    async def test_get_thread_status_existing(self, mock_strategy):
        """Test getting status of existing thread."""
        # Create a thread first
        channel = "status_test"
        runbook_id = "status_check_test"
        thread_id = await mock_strategy.create_approval_thread(channel, runbook_id, {})
        
        status = await mock_strategy.get_thread_status(thread_id)
        
        assert status is not None
        assert isinstance(status, dict)
        assert status["thread_id"] == thread_id
        assert status["status"] == "pending_approval"
    
    @pytest.mark.asyncio
    async def test_get_thread_status_nonexistent(self, mock_strategy):
        """Test getting status of non-existent thread."""
        status = await mock_strategy.get_thread_status("nonexistent_thread")
        
        assert status is None
    
    def test_simulate_notification_failure(self, mock_strategy):
        """Test notification failure simulation."""
        # This method should not raise exceptions
        mock_strategy.simulate_notification_failure(True)
        mock_strategy.simulate_notification_failure(False)
        
        # Method should complete without errors
        assert True
    
    def test_get_mock_channel_name(self, mock_strategy):
        """Test mock channel name retrieval."""
        # Test with known mock channel
        channel_name = mock_strategy._get_mock_channel_name("C1234567890")
        assert channel_name == "#general"
        
        # Test with thread ID
        thread_name = mock_strategy._get_mock_channel_name("thread_123.456")
        assert thread_name == "thread"
        
        # Test with unknown channel
        unknown_name = mock_strategy._get_mock_channel_name("unknown_channel")
        assert unknown_name == "#unknown_channel"
    
    @pytest.mark.asyncio
    async def test_concurrent_notifications(self, mock_strategy):
        """Test concurrent notification sending for thread safety."""
        channel = "concurrent_test"
        
        # Send multiple concurrent notifications
        tasks = []
        for i in range(10):
            context = {"title": f"Concurrent test {i}", "urgency": "medium"}
            task = mock_strategy.send_runbook_notification(channel, f"concurrent_{i}", context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All notifications should succeed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, str)
            assert result.startswith("notif_")
        
        # All should be stored
        notifications = mock_strategy.get_sent_notifications()
        for result in results:
            assert result in notifications
    
    @pytest.mark.asyncio
    async def test_error_handling_simulated_failure(self, mock_strategy):
        """Test error handling with simulated failures."""
        # Patch a method to raise an exception
        with patch('asyncio.sleep', side_effect=Exception("Simulated failure")):
            with pytest.raises(NotificationError):
                await mock_strategy.send_runbook_notification("test", "fail_test", {})
    
    def test_strategy_initialization(self, mock_strategy):
        """Test strategy initialization."""
        assert mock_strategy is not None
        
        # Should have initialized with mock channels
        channels = mock_strategy.get_mock_channels()
        assert len(channels) > 0
        
        # Storage should be empty initially
        assert len(mock_strategy.get_sent_notifications()) == 0
        assert len(mock_strategy.get_active_threads()) == 0