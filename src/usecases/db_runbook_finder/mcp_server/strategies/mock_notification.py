"""
Mock Notification Strategy Implementation.

This module provides a mock implementation of NotificationStrategy using
in-memory storage to simulate Slack notifications for development and testing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import random
import uuid

from .protocols import NotificationStrategyABC
from ..exceptions import NotificationError, MCPRunbookError

logger = logging.getLogger(__name__)


class MockNotificationStrategy(NotificationStrategyABC):
    """
    Mock notification strategy implementation.
    
    Uses in-memory storage to simulate Slack notifications, approval threads,
    and completion summaries. Implements NotificationStrategy protocol through
    structural subtyping.
    """
    
    def __init__(self):
        """Initialize mock notification strategy with in-memory storage."""
        # In-memory storage for mock notifications
        self._sent_notifications: Dict[str, Dict[str, Any]] = {}
        self._active_threads: Dict[str, Dict[str, Any]] = {}
        self._thread_messages: Dict[str, List[Dict[str, Any]]] = {}
        self._completion_summaries: Dict[str, Dict[str, Any]] = {}
        
        # Mock channels for testing
        self._mock_channels = {
            "general": "C1234567890",
            "incidents": "C2345678901", 
            "runbooks": "C3456789012",
            "alerts": "C4567890123"
        }
        
        logger.info(f"MockNotificationStrategy initialized")
    
    async def health_check(self) -> bool:
        """
        Mock health check - always returns True.
        
        Returns:
            True (mock implementation is always healthy)
        """
        return True
    
    # NotificationStrategy Protocol Implementation
    async def send_runbook_notification(self, channel: str, runbook_id: str, 
                                      context: Dict[str, Any]) -> str:
        """
        Send mock runbook discovery notification.
        
        Args:
            channel: Mock channel identifier
            runbook_id: Associated runbook identifier
            context: Notification context including title, description, urgency
            
        Returns:
            Mock notification/thread ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            notification_id = f"notif_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Prepare notification data
            title = context.get("title", f"Mock Runbook Found: {runbook_id}")
            description = context.get("description", "A relevant mock runbook has been discovered")
            urgency = context.get("urgency", "medium")
            incident_id = context.get("incident_id", "")
            
            # Create mock message based on urgency
            urgency_emoji = {"high": "🚨", "medium": "📋", "low": "ℹ️"}.get(urgency, "📋")
            
            mock_message = f"{urgency_emoji} **{title}**\\n\\n"
            mock_message += f"**Description:** {description}\\n"
            mock_message += f"**Runbook ID:** `{runbook_id}`\\n"
            
            if incident_id:
                mock_message += f"**Incident ID:** `{incident_id}`\\n"
            
            # Add additional context
            if "runbook_url" in context:
                mock_message += f"**URL:** {context['runbook_url']}\\n"
            if "categories" in context and context["categories"]:
                categories_str = ", ".join(context["categories"])
                mock_message += f"**Categories:** {categories_str}\\n"
            
            mock_message += f"\\n*Mock notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Store notification
            notification_data = {
                "notification_id": notification_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "runbook_id": runbook_id,
                "context": context,
                "message": mock_message,
                "urgency": urgency,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent",
                "source": "mock"
            }
            
            self._sent_notifications[notification_id] = notification_data
            
            # Initialize thread messages if it's a new thread
            if notification_id not in self._thread_messages:
                self._thread_messages[notification_id] = []
            
            self._thread_messages[notification_id].append({
                "message_id": f"msg_{random.randint(100000, 999999)}",
                "content": mock_message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "notification",
                "author": "mock_runbook_bot"
            })
            
            logger.info(f"Mock sent runbook notification {notification_id} for runbook {runbook_id} to channel {channel}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Mock failed to send runbook notification: {e}")
            raise NotificationError(channel, f"Failed to send runbook notification: {e}")
    
    async def create_approval_thread(self, channel: str, runbook_id: str, 
                                   context: Dict[str, Any]) -> str:
        """
        Create mock approval thread for runbook execution requiring approval.
        
        Args:
            channel: Mock channel for the approval thread
            runbook_id: Runbook requiring approval
            context: Approval context including procedure, risks, approvers
            
        Returns:
            Mock thread ID for the approval process
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            thread_id = f"thread_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Prepare approval data
            title = context.get("title", f"Mock Approval Required: {runbook_id}")
            procedure = context.get("procedure", "Execute mock runbook procedure")
            risk_level = context.get("risk_level", "medium")
            incident_id = context.get("incident_id", "")
            approvers = context.get("approvers", ["mock_approver_1", "mock_approver_2"])
            
            # Create mock approval message
            risk_emoji = {"high": "⚠️", "medium": "⚡", "low": "✅"}.get(risk_level, "⚡")
            
            mock_message = f"{risk_emoji} **MOCK APPROVAL REQUIRED**\\n\\n"
            mock_message += f"**Runbook:** `{runbook_id}`\\n"
            mock_message += f"**Procedure:** {procedure}\\n"
            mock_message += f"**Risk Level:** {risk_level.upper()}\\n"
            
            if incident_id:
                mock_message += f"**Incident:** `{incident_id}`\\n"
            
            if approvers:
                approvers_str = ", ".join([f"@{approver}" for approver in approvers])
                mock_message += f"**Approvers:** {approvers_str}\\n"
            
            mock_message += f"\\n**Mock Details:**\\n"
            if "description" in context:
                mock_message += f"{context['description']}\\n"
            if "estimated_duration" in context:
                mock_message += f"Estimated Duration: {context['estimated_duration']}\\n"
            if "rollback_procedure" in context:
                mock_message += f"Rollback Available: Yes\\n"
            
            mock_message += f"\\n*Mock approval requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Generate mock correlation ID
            correlation_id = context.get("correlation_id", f"approval_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
            
            # Store thread information
            thread_data = {
                "thread_id": thread_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "runbook_id": runbook_id,
                "correlation_id": correlation_id,
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "context": context,
                "approvers": approvers,
                "risk_level": risk_level,
                "approval_message": mock_message,
                "source": "mock"
            }
            
            self._active_threads[thread_id] = thread_data
            
            # Initialize thread messages
            if thread_id not in self._thread_messages:
                self._thread_messages[thread_id] = []
            
            # Add initial approval request message
            self._thread_messages[thread_id].append({
                "message_id": f"msg_{random.randint(100000, 999999)}",
                "content": mock_message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "approval_request",
                "author": "mock_runbook_bot"
            })
            
            # Simulate approval buttons/question
            self._thread_messages[thread_id].append({
                "message_id": f"msg_{random.randint(100000, 999999)}",
                "content": f"Do you approve the execution of runbook `{runbook_id}`? [Mock Buttons: Yes/No]",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "approval_question",
                "author": "mock_runbook_bot",
                "correlation_id": correlation_id
            })
            
            logger.info(f"Mock created approval thread {thread_id} for runbook {runbook_id} in channel {channel}")
            return thread_id
            
        except Exception as e:
            logger.error(f"Mock failed to create approval thread: {e}")
            raise NotificationError(channel, f"Failed to create approval thread: {e}")
    
    async def update_thread_status(self, thread_id: str, status: str, 
                                 results: Dict[str, Any]) -> bool:
        """
        Update mock thread with execution status and results.
        
        Args:
            thread_id: Thread to update
            status: Current status (approved, rejected, executing, completed, failed)
            results: Execution results including success, errors, duration
            
        Returns:
            True if update successful
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            # Update local tracking
            if thread_id in self._active_threads:
                self._active_threads[thread_id]["status"] = status
                self._active_threads[thread_id]["last_updated"] = datetime.utcnow().isoformat()
                self._active_threads[thread_id]["results"] = results
            else:
                # Create mock thread if not found
                self._active_threads[thread_id] = {
                    "thread_id": thread_id,
                    "channel": "unknown",
                    "runbook_id": "unknown",
                    "status": status,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat(),
                    "results": results,
                    "source": "mock_auto_created"
                }
                logger.warning(f"Mock auto-created thread data for {thread_id}")
            
            # Prepare status update message
            status_emojis = {
                "approved": "✅",
                "rejected": "❌", 
                "executing": "⚙️",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "⏹️"
            }
            
            emoji = status_emojis.get(status, "📊")
            mock_message = f"\\n{emoji} **MOCK STATUS UPDATE: {status.upper()}**\\n"
            
            if "success" in results:
                mock_message += f"**Success:** {'Yes' if results['success'] else 'No'}\\n"
            if "duration" in results:
                mock_message += f"**Duration:** {results['duration']}\\n"
            if "steps_completed" in results:
                mock_message += f"**Steps Completed:** {results['steps_completed']}\\n"
            if "error" in results:
                mock_message += f"**Error:** `{results['error']}`\\n"
            if "output" in results:
                output_preview = results["output"][:200] + "..." if len(results["output"]) > 200 else results["output"]
                mock_message += f"**Output:** ```{output_preview}```\\n"
            
            mock_message += f"\\n*Mock status updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Add message to thread
            if thread_id not in self._thread_messages:
                self._thread_messages[thread_id] = []
            
            self._thread_messages[thread_id].append({
                "message_id": f"msg_{random.randint(100000, 999999)}",
                "content": mock_message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "status_update",
                "author": "mock_runbook_bot",
                "status": status,
                "results": results
            })
            
            logger.info(f"Mock updated thread {thread_id} with status {status}")
            return True
            
        except Exception as e:
            logger.error(f"Mock failed to update thread status: {e}")
            raise NotificationError("unknown", f"Failed to update thread status: {e}")
    
    async def send_completion_summary(self, channel: str, summary: Dict[str, Any]) -> str:
        """
        Send mock workflow completion summary with results and metrics.
        
        Args:
            channel: Target channel for summary
            summary: Summary data including workflow results, metrics, recommendations
            
        Returns:
            Mock message ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            message_id = f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Prepare completion summary
            workflow_name = summary.get("workflow_name", "Mock Runbook Workflow")
            total_runbooks = summary.get("total_runbooks_processed", random.randint(3, 10))
            successful_executions = summary.get("successful_executions", random.randint(2, total_runbooks))
            failed_executions = summary.get("failed_executions", total_runbooks - successful_executions)
            total_duration = summary.get("total_duration", f"{random.randint(15, 120)} minutes")
            
            # Calculate success rate
            if total_runbooks > 0:
                success_rate = (successful_executions / total_runbooks) * 100
            else:
                success_rate = 0
                
            # Choose emoji based on success rate
            if success_rate >= 90:
                status_emoji = "🎉"
            elif success_rate >= 70:
                status_emoji = "✅"
            else:
                status_emoji = "⚠️"
                
            mock_message = f"{status_emoji} **MOCK WORKFLOW COMPLETED: {workflow_name}**\\n\\n"
            mock_message += f"**Mock Summary:**\\n"
            mock_message += f"• Total Runbooks: {total_runbooks}\\n"
            mock_message += f"• Successful: {successful_executions}\\n"
            mock_message += f"• Failed: {failed_executions}\\n"
            mock_message += f"• Success Rate: {success_rate:.1f}%\\n"
            mock_message += f"• Total Duration: {total_duration}\\n"
            
            # Add mock detailed results
            mock_results = [
                {"runbook_id": "mock_db_001", "status": "success", "duration": "12 min"},
                {"runbook_id": "mock_perf_001", "status": "success", "duration": "8 min"},
                {"runbook_id": "mock_backup_001", "status": "failed", "duration": "5 min"}
            ]
            
            if "results" in summary:
                results = summary["results"][:3]  # Use provided results
            else:
                results = mock_results[:3]  # Use mock results
                
            mock_message += f"\\n**Mock Results:**\\n"
            for result in results:
                runbook_id = result.get("runbook_id", "unknown")
                status = result.get("status", "unknown") 
                result_emoji = "✅" if status == "success" else "❌"
                mock_message += f"{result_emoji} {runbook_id}: {status}\\n"
            
            # Add mock recommendations
            mock_recommendations = [
                "Consider automating runbook execution for routine tasks",
                "Review failed runbooks for process improvements"
            ]
            
            recommendations = summary.get("recommendations", mock_recommendations)
            if recommendations:
                mock_message += f"\\n**Mock Recommendations:**\\n"
                for rec in recommendations[:2]:
                    mock_message += f"• {rec}\\n"
            
            # Add mock performance metrics
            mock_message += f"\\n**Mock Performance:**\\n"
            mock_message += f"• Avg Execution Time: {random.randint(5, 20)} minutes\\n"
            mock_message += f"• Incidents Resolved: {random.randint(1, 5)}\\n"
            
            mock_message += f"\\n*Mock completion summary generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Store completion summary
            summary_data = {
                "message_id": message_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "workflow_name": workflow_name,
                "summary": summary,
                "message": mock_message,
                "sent_at": datetime.utcnow().isoformat(),
                "success_rate": success_rate,
                "total_runbooks": total_runbooks,
                "source": "mock"
            }
            
            self._completion_summaries[message_id] = summary_data
            
            logger.info(f"Mock sent completion summary {message_id} to channel {channel}")
            return message_id
            
        except Exception as e:
            logger.error(f"Mock failed to send completion summary: {e}")
            raise NotificationError(channel, f"Failed to send completion summary: {e}")
    
    async def send_alert_notification(self, channel: str, alert_type: str, 
                                    message: str, urgency: str = "medium") -> str:
        """
        Send mock alert notification for critical runbook events.
        
        Args:
            channel: Target channel
            alert_type: Type of alert (error, warning, info)
            message: Alert message content
            urgency: Alert urgency level
            
        Returns:
            Mock notification ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            alert_id = f"alert_{alert_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Format alert message
            alert_emojis = {
                "error": "🚨",
                "warning": "⚠️", 
                "info": "ℹ️",
                "success": "✅"
            }
            
            emoji = alert_emojis.get(alert_type, "📢")
            mock_formatted_message = f"{emoji} **MOCK ALERT: {alert_type.upper()}**\\n\\n{message}\\n\\n*Mock alert sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Store alert
            alert_data = {
                "alert_id": alert_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "alert_type": alert_type,
                "urgency": urgency,
                "original_message": message,
                "formatted_message": mock_formatted_message,
                "sent_at": datetime.utcnow().isoformat(),
                "source": "mock"
            }
            
            # Store in notifications for tracking
            self._sent_notifications[alert_id] = alert_data
            
            logger.info(f"Mock sent alert notification {alert_id} to channel {channel}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Mock failed to send alert notification: {e}")
            raise NotificationError(channel, f"Failed to send alert: {e}")
    
    async def send_escalation_alert(self, channel: str, incident_id: str, escalation_context: Dict[str, Any]) -> str:
        """
        Send mock escalation alert when runbook execution fails or requires human intervention.
        
        Args:
            channel: Communication channel for escalation
            incident_id: Associated incident
            escalation_context: Details requiring escalation
            
        Returns:
            Alert message ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            alert_id = f"escalation_{incident_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Extract escalation context
            reason = escalation_context.get("reason", "Mock escalation required")
            severity = escalation_context.get("severity", "high")
            runbook_id = escalation_context.get("runbook_id", "unknown")
            error_details = escalation_context.get("error_details", "Mock execution failure")
            
            # Create escalation alert message
            severity_emoji = {"critical": "🔥", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}.get(severity, "⚠️")
            
            mock_message = f"{severity_emoji} **MOCK ESCALATION ALERT**\\n\\n"
            mock_message += f"**Incident ID:** `{incident_id}`\\n"
            mock_message += f"**Runbook ID:** `{runbook_id}`\\n"
            mock_message += f"**Severity:** {severity.upper()}\\n"
            mock_message += f"**Reason:** {reason}\\n"
            mock_message += f"**Error Details:** {error_details}\\n"
            
            # Add required actions
            if "required_actions" in escalation_context:
                actions = escalation_context["required_actions"]
                if isinstance(actions, list):
                    mock_message += f"\\n**Required Actions:**\\n"
                    for i, action in enumerate(actions, 1):
                        mock_message += f"{i}. {action}\\n"
            
            # Add escalation teams
            if "escalation_teams" in escalation_context:
                teams = escalation_context["escalation_teams"]
                if isinstance(teams, list):
                    teams_str = ", ".join([f"@{team}" for team in teams])
                    mock_message += f"\\n**Escalation Teams:** {teams_str}\\n"
            
            mock_message += f"\\n*Mock escalation alert sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Store escalation alert
            alert_data = {
                "alert_id": alert_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "incident_id": incident_id,
                "escalation_context": escalation_context,
                "message": mock_message,
                "severity": severity,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent",
                "source": "mock"
            }
            
            self._sent_notifications[alert_id] = alert_data
            
            logger.warning(f"Mock sent escalation alert {alert_id} for incident {incident_id} to channel {channel}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Mock failed to send escalation alert: {e}")
            raise NotificationError(channel, f"Failed to send escalation alert: {e}")
    
    async def create_thread(self, channel: str, message: str, formatting: Optional[Any] = None) -> str:
        """
        Create new mock communication thread.
        
        Args:
            channel: Communication channel
            message: Initial message content
            formatting: Optional formatting (bold, italic, code, etc.)
            
        Returns:
            Thread ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            thread_id = f"thread_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Apply mock formatting if specified
            formatted_message = message
            if formatting:
                if isinstance(formatting, dict):
                    if formatting.get("bold"):
                        formatted_message = f"**{formatted_message}**"
                    if formatting.get("italic"):
                        formatted_message = f"*{formatted_message}*"
                    if formatting.get("code"):
                        formatted_message = f"`{formatted_message}`"
                    if formatting.get("code_block"):
                        formatted_message = f"```\\n{formatted_message}\\n```"
            
            # Create thread data
            thread_data = {
                "thread_id": thread_id,
                "channel": channel,
                "channel_name": self._get_mock_channel_name(channel),
                "initial_message": message,
                "formatted_message": formatted_message,
                "formatting": formatting,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": "mock_user",
                "status": "active",
                "message_count": 1,
                "source": "mock"
            }
            
            self._active_threads[thread_id] = thread_data
            
            # Initialize thread messages
            if thread_id not in self._thread_messages:
                self._thread_messages[thread_id] = []
            
            # Add initial message
            initial_msg = {
                "message_id": f"msg_{random.randint(100000, 999999)}",
                "content": formatted_message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "initial",
                "author": "mock_user",
                "formatting": formatting
            }
            
            self._thread_messages[thread_id].append(initial_msg)
            
            logger.info(f"Mock created thread {thread_id} in channel {channel}")
            return thread_id
            
        except Exception as e:
            logger.error(f"Mock failed to create thread: {e}")
            raise NotificationError(channel, f"Failed to create thread: {e}")
    
    async def send_message(self, thread_id: str, message: str, formatting: Optional[Any] = None) -> str:
        """
        Send message to existing mock thread.
        
        Args:
            thread_id: Existing thread
            message: Message content
            formatting: Optional formatting
            
        Returns:
            Message ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            message_id = f"msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(100000, 999999)}"
            
            # Check if thread exists
            if thread_id not in self._active_threads:
                logger.warning(f"Thread {thread_id} not found, creating mock thread reference")
                # Create a basic thread reference
                self._active_threads[thread_id] = {
                    "thread_id": thread_id,
                    "channel": "unknown",
                    "created_at": datetime.utcnow().isoformat(),
                    "status": "active",
                    "message_count": 0,
                    "source": "mock"
                }
                self._thread_messages[thread_id] = []
            
            # Apply mock formatting if specified
            formatted_message = message
            if formatting:
                if isinstance(formatting, dict):
                    if formatting.get("bold"):
                        formatted_message = f"**{formatted_message}**"
                    if formatting.get("italic"):
                        formatted_message = f"*{formatted_message}*"
                    if formatting.get("code"):
                        formatted_message = f"`{formatted_message}`"
                    if formatting.get("code_block"):
                        formatted_message = f"```\\n{formatted_message}\\n```"
            
            # Create message data
            message_data = {
                "message_id": message_id,
                "thread_id": thread_id,
                "content": formatted_message,
                "original_content": message,
                "formatting": formatting,
                "timestamp": datetime.utcnow().isoformat(),
                "author": "mock_user",
                "type": "reply",
                "source": "mock"
            }
            
            # Add to thread messages
            self._thread_messages[thread_id].append(message_data)
            
            # Update thread message count
            self._active_threads[thread_id]["message_count"] += 1
            self._active_threads[thread_id]["last_message_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Mock sent message {message_id} to thread {thread_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Mock failed to send message: {e}")
            raise NotificationError(thread_id, f"Failed to send message: {e}")
    
    # Helper Methods
    def _get_mock_channel_name(self, channel: str) -> str:
        """Get mock channel name from identifier."""
        # Reverse lookup in mock channels
        for name, id_val in self._mock_channels.items():
            if id_val == channel:
                return f"#{name}"
        
        # If it looks like a thread ID, return as thread
        if channel.startswith("thread_") or "." in channel:
            return "thread"
        
        # Return as-is for other channels
        return f"#{channel}"
    
    # Mock-specific Methods for Testing
    def get_sent_notifications(self) -> Dict[str, Dict[str, Any]]:
        """Get all sent notifications for testing and debugging."""
        return self._sent_notifications.copy()
    
    def get_active_threads(self) -> Dict[str, Dict[str, Any]]:
        """Get all active threads for monitoring and debugging."""
        return self._active_threads.copy()
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a specific thread."""
        return self._thread_messages.get(thread_id, []).copy()
    
    def get_all_thread_messages(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all thread messages for testing."""
        return {tid: msgs.copy() for tid, msgs in self._thread_messages.items()}
    
    def get_completion_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get all completion summaries for testing and debugging."""
        return self._completion_summaries.copy()
    
    def clear_data(self) -> None:
        """Clear all stored data for testing."""
        self._sent_notifications.clear()
        self._active_threads.clear()
        self._thread_messages.clear()
        self._completion_summaries.clear()
        logger.info("Mock notification storage cleared")
    
    def simulate_approval_response(self, thread_id: str, approved: bool, approver: str = "mock_approver") -> bool:
        """Simulate an approval response for testing."""
        if thread_id not in self._active_threads:
            logger.warning(f"Thread {thread_id} not found for approval simulation")
            return False
        
        thread_data = self._active_threads[thread_id]
        new_status = "approved" if approved else "rejected"
        
        # Update thread status
        thread_data["status"] = new_status
        thread_data["approved_by"] = approver
        thread_data["approval_timestamp"] = datetime.utcnow().isoformat()
        
        # Add approval message to thread
        if thread_id not in self._thread_messages:
            self._thread_messages[thread_id] = []
        
        approval_emoji = "✅" if approved else "❌"
        approval_message = f"{approval_emoji} **Mock Approval Response**\\n\\n"
        approval_message += f"Approver: @{approver}\\n"
        approval_message += f"Decision: {'APPROVED' if approved else 'REJECTED'}\\n"
        approval_message += f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        self._thread_messages[thread_id].append({
            "message_id": f"msg_{random.randint(100000, 999999)}",
            "content": approval_message,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "approval_response",
            "author": approver,
            "approved": approved
        })
        
        logger.info(f"Mock simulated approval response for thread {thread_id}: {'approved' if approved else 'rejected'}")
        return True
    
    def get_mock_channels(self) -> Dict[str, str]:
        """Get available mock channels."""
        return self._mock_channels.copy()
    
    def add_mock_channel(self, name: str, channel_id: str) -> None:
        """Add a mock channel for testing."""
        self._mock_channels[name] = channel_id
        logger.info(f"Added mock channel: #{name} ({channel_id})")
    
    async def get_thread_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific thread."""
        return self._active_threads.get(thread_id)
    
    def simulate_notification_failure(self, should_fail: bool = True) -> None:
        """Simulate notification failures for testing error handling."""
        # This would be used in tests to simulate failures
        if should_fail:
            logger.warning("Mock notification strategy set to simulate failures")
        else:
            logger.info("Mock notification strategy set to normal operation")