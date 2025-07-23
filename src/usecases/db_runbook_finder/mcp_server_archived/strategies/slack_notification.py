"""
Slack Notification Strategy Implementation.

This module provides the NotificationStrategy implementation that integrates
with the existing Slack communication tool for runbook-related notifications.
"""

import logging
from typing import Dict, Any, Optional
import httpx
import os
from datetime import datetime

from .protocols import NotificationStrategyABC
from ..exceptions import NotificationError

logger = logging.getLogger(__name__)


class SlackNotificationStrategy(NotificationStrategyABC):
    """
    Slack-based notification strategy implementation.
    
    Integrates with the existing Slack communication tool via HTTP API
    for runbook discovery notifications, approval threads, and status updates.
    Implements NotificationStrategy protocol through structural subtyping.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize Slack notification strategy.
        
        Args:
            base_url: Base URL for Slack communication tool API (defaults to env var)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url or os.getenv("SLACK_TOOL_URL", "http://localhost:8002")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # In-memory storage for thread tracking (would be Redis/MongoDB in production)
        self._active_threads: Dict[str, Dict[str, Any]] = {}
        self._notification_history: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"SlackNotificationStrategy initialized with base_url: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Slack communication tool API."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'RunbookRepositoryMCP/1.0'
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """
        Check if Slack communication tool is accessible and healthy.
        
        Returns:
            True if Slack tool is healthy
        """
        try:
            client = await self._get_client()
            # Try to send a test message to verify connectivity
            test_payload = {
                "message": "Health check - please ignore",
                "formatting": "code"
            }
            response = await client.post(f"{self.base_url}/messages/", json=test_payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
            return False
    
    # NotificationStrategy Protocol Implementation
    async def send_runbook_notification(self, channel: str, runbook_id: str, 
                                      context: Dict[str, Any]) -> str:
        """
        Send runbook discovery notification to Slack channel.
        
        Args:
            channel: Slack channel identifier (can be channel name or thread_id)
            runbook_id: Associated runbook identifier
            context: Notification context including title, description, urgency
            
        Returns:
            Notification/thread ID
        """
        try:
            client = await self._get_client()
            
            # Prepare notification message
            title = context.get("title", f"Runbook Found: {runbook_id}")
            description = context.get("description", "A relevant runbook has been discovered")
            urgency = context.get("urgency", "medium")
            incident_id = context.get("incident_id", "")
            
            # Format message based on urgency
            urgency_emoji = {"high": "🚨", "medium": "📋", "low": "ℹ️"}.get(urgency, "📋")
            
            message = f"{urgency_emoji} **{title}**\n\n"
            message += f"**Description:** {description}\n"
            message += f"**Runbook ID:** `{runbook_id}`\n"
            
            if incident_id:
                message += f"**Incident ID:** `{incident_id}`\n"
            
            # Add runbook details if available
            if "runbook_url" in context:
                message += f"**URL:** {context['runbook_url']}\n"
            if "categories" in context and context["categories"]:
                categories_str = ", ".join(context["categories"])
                message += f"**Categories:** {categories_str}\n"
            if "estimated_steps" in context:
                message += f"**Estimated Steps:** {context['estimated_steps']}\n"
            
            message += f"\n*Discovered at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Send message payload
            payload = {
                "message": message,
                "formatting": "bold" if urgency == "high" else None
            }
            
            # If channel is a thread_id, send to thread, otherwise create new thread
            if channel.startswith("thread_") or "." in channel:  # Slack timestamp format
                payload["thread_id"] = channel
            
            response = await client.post(f"{self.base_url}/messages/", json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                notification_id = response_data.get("thread_id", f"notif_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                
                # Store notification for tracking
                self._notification_history[notification_id] = {
                    "notification_id": notification_id,
                    "channel": channel,
                    "runbook_id": runbook_id,
                    "context": context,
                    "sent_at": datetime.utcnow().isoformat(),
                    "message": message
                }
                
                logger.info(f"Sent runbook notification {notification_id} for runbook {runbook_id}")
                return notification_id
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send runbook notification for {runbook_id}: {e}")
            raise NotificationError(channel, f"Failed to send runbook notification: {e}")
        
        return ""
    
    async def create_approval_thread(self, channel: str, runbook_id: str, 
                                   context: Dict[str, Any]) -> str:
        """
        Create approval thread for runbook execution requiring human approval.
        
        Args:
            channel: Slack channel for the approval thread
            runbook_id: Runbook requiring approval
            context: Approval context including procedure, risks, approvers
            
        Returns:
            Thread ID for the approval process
        """
        try:
            client = await self._get_client()
            
            # Prepare approval request message
            title = context.get("title", f"Approval Required: {runbook_id}")
            procedure = context.get("procedure", "Execute runbook procedure")
            risk_level = context.get("risk_level", "medium")
            incident_id = context.get("incident_id", "")
            approvers = context.get("approvers", [])
            
            # Format message
            risk_emoji = {"high": "⚠️", "medium": "⚡", "low": "✅"}.get(risk_level, "⚡")
            
            message = f"{risk_emoji} **APPROVAL REQUIRED**\n\n"
            message += f"**Runbook:** `{runbook_id}`\n"
            message += f"**Procedure:** {procedure}\n"
            message += f"**Risk Level:** {risk_level.upper()}\n"
            
            if incident_id:
                message += f"**Incident:** `{incident_id}`\n"
            if approvers:
                approvers_str = ", ".join([f"<@{approver}>" for approver in approvers])
                message += f"**Approvers:** {approvers_str}\n"
            
            message += "\n**Details:**\n"
            if "description" in context:
                message += f"{context['description']}\n"
            if "estimated_duration" in context:
                message += f"Estimated Duration: {context['estimated_duration']}\n"
            if "rollback_procedure" in context:
                message += "Rollback Available: Yes\n"
            
            message += f"\n*Approval requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Create the initial thread
            thread_payload = {
                "message": message,
                "formatting": "bold"
            }
            
            response = await client.post(f"{self.base_url}/messages/", json=thread_payload)
            
            if response.status_code == 200:
                response_data = response.json()
                thread_id = response_data.get("thread_id", f"approval_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                
                # Generate correlation ID for approval tracking
                correlation_id = context.get("correlation_id", f"approval_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                
                # Send approval question using the existing question API
                question_payload = {
                    "thread_id": thread_id,
                    "command_id": correlation_id,
                    "question": f"Do you approve the execution of runbook `{runbook_id}`?"
                }
                
                question_response = await client.post(f"{self.base_url}/questions/", json=question_payload)
                
                # Store thread information for tracking
                self._active_threads[thread_id] = {
                    "thread_id": thread_id,
                    "channel": channel,
                    "runbook_id": runbook_id,
                    "correlation_id": correlation_id,
                    "status": "pending_approval",
                    "created_at": datetime.utcnow().isoformat(),
                    "context": context,
                    "approvers": approvers,
                    "risk_level": risk_level
                }
                
                logger.info(f"Created approval thread {thread_id} for runbook {runbook_id}")
                return thread_id
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to create approval thread for {runbook_id}: {e}")
            raise NotificationError(channel, f"Failed to create approval thread: {e}")
        
        return ""
    
    async def update_thread_status(self, thread_id: str, status: str, 
                                 results: Dict[str, Any]) -> bool:
        """
        Update thread with execution status and results.
        
        Args:
            thread_id: Thread to update
            status: Current status (approved, rejected, executing, completed, failed)
            results: Execution results including success, errors, duration
            
        Returns:
            True if update successful
        """
        try:
            client = await self._get_client()
            
            # Update local tracking
            if thread_id in self._active_threads:
                self._active_threads[thread_id]["status"] = status
                self._active_threads[thread_id]["last_updated"] = datetime.utcnow().isoformat()
                self._active_threads[thread_id]["results"] = results
            
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
            message = f"\n{emoji} **STATUS UPDATE: {status.upper()}**\n"
            
            if "success" in results:
                message += f"**Success:** {'Yes' if results['success'] else 'No'}\n"
            if "duration" in results:
                message += f"**Duration:** {results['duration']}\n"
            if "steps_completed" in results:
                message += f"**Steps Completed:** {results['steps_completed']}\n"
            if "error" in results:
                message += f"**Error:** `{results['error']}`\n"
            if "output" in results:
                output_preview = results["output"][:200] + "..." if len(results["output"]) > 200 else results["output"]
                message += f"**Output:** ```{output_preview}```\n"
            
            message += f"\n*Updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Send status update to thread
            update_payload = {
                "thread_id": thread_id,
                "message": message,
                "formatting": "code" if status == "failed" else None
            }
            
            response = await client.post(f"{self.base_url}/messages/", json=update_payload)
            
            if response.status_code == 200:
                logger.info(f"Updated thread {thread_id} with status {status}")
                return True
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to update thread status {thread_id}: {e}")
            raise NotificationError("unknown", f"Failed to update thread status: {e}")
        
        return False
    
    async def send_completion_summary(self, channel: str, summary: Dict[str, Any]) -> str:
        """
        Send workflow completion summary with results and metrics.
        
        Args:
            channel: Target channel for summary
            summary: Summary data including workflow results, metrics, recommendations
            
        Returns:
            Message ID
        """
        try:
            client = await self._get_client()
            
            # Prepare completion summary message
            workflow_name = summary.get("workflow_name", "Runbook Workflow")
            total_runbooks = summary.get("total_runbooks_processed", 0)
            successful_executions = summary.get("successful_executions", 0)
            failed_executions = summary.get("failed_executions", 0)
            total_duration = summary.get("total_duration", "Unknown")
            
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
                
            message = f"{status_emoji} **WORKFLOW COMPLETED: {workflow_name}**\n\n"
            message += "**Summary:**\n"
            message += f"• Total Runbooks: {total_runbooks}\n"
            message += f"• Successful: {successful_executions}\n"
            message += f"• Failed: {failed_executions}\n"
            message += f"• Success Rate: {success_rate:.1f}%\n"
            message += f"• Total Duration: {total_duration}\n"
            
            # Add detailed results if available
            if "results" in summary and summary["results"]:
                message += "\n**Results:**\n"
                for result in summary["results"][:3]:  # Show first 3 results
                    runbook_id = result.get("runbook_id", "Unknown")
                    status = result.get("status", "unknown")
                    result_emoji = "✅" if status == "success" else "❌"
                    message += f"{result_emoji} {runbook_id}: {status}\n"
                
                if len(summary["results"]) > 3:
                    remaining = len(summary["results"]) - 3
                    message += f"... and {remaining} more results\n"
            
            # Add recommendations if available
            if "recommendations" in summary and summary["recommendations"]:
                message += "\n**Recommendations:**\n"
                for rec in summary["recommendations"][:2]:  # Show first 2 recommendations
                    message += f"• {rec}\n"
            
            # Add metrics if available
            if "metrics" in summary:
                metrics = summary["metrics"]
                if "avg_execution_time" in metrics:
                    message += "\n**Performance:**\n"
                    message += f"• Avg Execution Time: {metrics['avg_execution_time']}\n"
                if "total_incidents_resolved" in metrics:
                    message += f"• Incidents Resolved: {metrics['total_incidents_resolved']}\n"
            
            message += f"\n*Completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            # Send completion summary
            payload = {
                "message": message,
                "formatting": "bold"
            }
            
            # If channel is a thread_id, send to thread
            if channel.startswith("thread_") or "." in channel:
                payload["thread_id"] = channel
            
            response = await client.post(f"{self.base_url}/messages/", json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get("thread_id", f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                
                logger.info(f"Sent completion summary {message_id} to channel {channel}")
                return message_id
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send completion summary to {channel}: {e}")
            raise NotificationError(channel, f"Failed to send completion summary: {e}")
        
        return ""
    
    async def send_alert_notification(self, channel: str, alert_type: str, 
                                    message: str, urgency: str = "medium") -> str:
        """
        Send alert notification for critical runbook events.
        
        Args:
            channel: Target channel
            alert_type: Type of alert (error, warning, info)
            message: Alert message content
            urgency: Alert urgency level
            
        Returns:
            Notification ID
        """
        try:
            client = await self._get_client()
            
            # Format alert message
            alert_emojis = {
                "error": "🚨",
                "warning": "⚠️", 
                "info": "ℹ️",
                "success": "✅"
            }
            
            emoji = alert_emojis.get(alert_type, "📢")
            formatted_message = f"{emoji} **ALERT: {alert_type.upper()}**\n\n{message}\n\n*Alert sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
            
            payload = {
                "message": formatted_message,
                "formatting": "bold" if urgency == "high" else None
            }
            
            if channel.startswith("thread_") or "." in channel:
                payload["thread_id"] = channel
            
            response = await client.post(f"{self.base_url}/messages/", json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                alert_id = response_data.get("thread_id", f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                
                logger.info(f"Sent alert notification {alert_id} to channel {channel}")
                return alert_id
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send alert notification to {channel}: {e}")
            raise NotificationError(channel, f"Failed to send alert: {e}")
        
        return ""
    
    # Helper Methods
    def get_active_threads(self) -> Dict[str, Dict[str, Any]]:
        """Get all active threads for monitoring and debugging."""
        return self._active_threads.copy()
    
    def get_notification_history(self) -> Dict[str, Dict[str, Any]]:
        """Get notification history for auditing and debugging."""
        return self._notification_history.copy()
    
    def clear_data(self) -> None:
        """Clear all stored data for testing."""
        self._active_threads.clear()
        self._notification_history.clear()
    
    async def get_thread_status(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a specific thread.
        
        Args:
            thread_id: Thread to check
            
        Returns:
            Thread status dictionary or None if not found
        """
        return self._active_threads.get(thread_id)
    
    async def cancel_approval_thread(self, thread_id: str, reason: str = "Cancelled by system") -> bool:
        """
        Cancel an active approval thread.
        
        Args:
            thread_id: Thread to cancel
            reason: Cancellation reason
            
        Returns:
            True if cancellation successful
        """
        try:
            if thread_id in self._active_threads:
                # Update thread status
                await self.update_thread_status(thread_id, "cancelled", {"reason": reason})
                
                # Remove from active threads
                del self._active_threads[thread_id]
                
                logger.info(f"Cancelled approval thread {thread_id}: {reason}")
                return True
            else:
                logger.warning(f"Thread {thread_id} not found for cancellation")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel thread {thread_id}: {e}")
            return False