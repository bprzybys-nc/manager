"""
Slack MCP Client Wrapper for Database Decommissioning.

This module provides a Manager-integrated wrapper for the Slack MCP client,
enabling enhanced Slack operations for database decommissioning workflows.

Manager Integration:
- Enhanced notification system with Manager context
- Tenant-aware Slack messaging
- Graceful degradation for Slack API limitations
- Manager-specific logging and error handling

GraphMCP Preservation:
- Full SlackMCPClient compatibility
- Standard Slack MCP tool support
- Message posting and channel management patterns
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.clients.slack import SlackMCPClient
from src.frameworks.graphmcp.clients.base import MCPToolError

# Local imports
from .base import BaseMCPClientWrapper


class SlackClientWrapper(BaseMCPClientWrapper):
    """
    Slack MCP client wrapper with Manager integration.
    
    Provides enhanced Slack operations for database decommissioning workflows
    while maintaining full GraphMCP framework compatibility.
    """

    @property
    def client_class(self) -> type:
        """Return the GraphMCP Slack client class."""
        return SlackMCPClient

    @property
    def server_name(self) -> str:
        """Return the MCP server name for Slack client."""
        return "ovr_slack"

    async def post_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Post message to Slack channel with Manager enhancements.

        Args:
            channel_id: Slack channel ID (e.g., "C01234567") or channel name
            text: Message text to post
            thread_ts: Optional thread timestamp for threaded replies
            blocks: Optional blocks for rich message formatting
            attachments: Optional message attachments (legacy)

        Returns:
            Enhanced message posting result with Manager metadata
        """
        try:
            self.logger.log_info(
                f"Posting message to Slack channel: {channel_id}",
                {"message_length": len(text), "threaded": thread_ts is not None}
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "post_message",
                    Exception("Slack client not available"),
                    {
                        "channel": channel_id,
                        "text": text,
                        "message_skipped": True,
                        "notification_disabled": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.post_message(channel_id, text, thread_ts, blocks, attachments)

            # Enhance result with Manager metadata
            enhanced_result = self._create_enhanced_result(
                result,
                "post_message",
                channel=channel_id,
                message_length=len(text),
                threaded=thread_ts is not None,
            )

            if result.get("success"):
                self.logger.log_info(
                    f"Successfully posted message to {channel_id}",
                    {"message_ts": result.get("ts")}
                )
            else:
                self.logger.log_warning(
                    f"Failed to post message to {channel_id}",
                    {"error": result.get("error")}
                )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to post message to {channel_id}", e)
            return self._handle_graceful_degradation(
                "post_message",
                e,
                {
                    "channel": channel_id,
                    "text": text,
                    "message_failed": True,
                }
            )

    async def post_database_decommission_notification(
        self,
        channel_id: str,
        database_name: str,
        repository: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Post database decommissioning notification with structured formatting.

        Args:
            channel_id: Slack channel ID or name
            database_name: Name of database being decommissioned
            repository: Repository being processed
            status: Status of decommissioning (started, progress, completed, failed)
            details: Additional details to include in notification

        Returns:
            Notification posting result
        """
        try:
            # Create structured message based on status
            if status == "started":
                emoji = "🚀"
                title = "Database Decommissioning Started"
                color = "#36a64f"  # Green
            elif status == "progress":
                emoji = "⚙️"
                title = "Database Decommissioning In Progress"
                color = "#ff9f00"  # Orange
            elif status == "completed":
                emoji = "✅"
                title = "Database Decommissioning Completed"
                color = "#36a64f"  # Green
            elif status == "failed":
                emoji = "❌"
                title = "Database Decommissioning Failed"
                color = "#ff0000"  # Red
            else:
                emoji = "📊"
                title = "Database Decommissioning Update"
                color = "#0099cc"  # Blue

            # Build message text
            message_parts = [
                f"{emoji} **{title}**",
                f"",
                f"**Database:** {database_name}",
                f"**Repository:** {repository}",
                f"**Status:** {status.title()}",
            ]

            # Add tenant context if available
            if self.tenant_id:
                message_parts.append(f"**Tenant:** {self.tenant_id}")

            # Add additional details
            if details:
                message_parts.append("")
                message_parts.append("**Details:**")
                for key, value in details.items():
                    if isinstance(value, (int, float)):
                        message_parts.append(f"• {key.replace('_', ' ').title()}: {value}")
                    elif isinstance(value, str) and len(value) < 100:
                        message_parts.append(f"• {key.replace('_', ' ').title()}: {value}")

            message_text = "\n".join(message_parts)

            # Create blocks for rich formatting
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                }
            ]

            # Add context block with workflow info
            context_elements = []
            if self.workflow_id:
                context_elements.append(f"Workflow ID: {self.workflow_id}")
            
            context_elements.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

            if context_elements:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": " | ".join(context_elements)
                        }
                    ]
                })

            # Post the message
            result = await self.post_message(
                channel_id=channel_id,
                text=message_text,  # Fallback text for notifications
                blocks=blocks,
            )

            # Enhance with notification-specific metadata
            if result.get("success"):
                result["notification_type"] = "database_decommission"
                result["database_name"] = database_name
                result["repository"] = repository
                result["status"] = status

            return result

        except Exception as e:
            self.logger.log_error(
                f"Failed to post database decommission notification", e,
                {"database": database_name, "repository": repository, "status": status}
            )
            return self._handle_graceful_degradation(
                "post_database_decommission_notification",
                e,
                {
                    "channel": channel_id,
                    "database_name": database_name,
                    "repository": repository,
                    "status": status,
                    "notification_failed": True,
                }
            )

    async def list_channels(
        self,
        types: str = "public_channel,private_channel",
        exclude_archived: bool = True,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        List available Slack channels with Manager enhancements.

        Args:
            types: Comma-separated list of channel types to include
            exclude_archived: Whether to exclude archived channels
            limit: Maximum number of channels to return

        Returns:
            Enhanced list of channel information
        """
        try:
            self.logger.log_info("Listing Slack channels")

            # Check if client is available
            if not await self.is_available():
                self.logger.log_warning("Slack client not available, returning empty channel list")
                return []

            client = await self._initialize_client()
            channels = await client.list_channels(types, exclude_archived, limit)

            self.logger.log_info(f"Retrieved {len(channels)} Slack channels")
            return channels

        except Exception as e:
            self.logger.log_error("Failed to list Slack channels", e)
            return []

    async def add_reaction(
        self, channel: str, timestamp: str, name: str
    ) -> Dict[str, Any]:
        """
        Add emoji reaction to message with Manager tracking.

        Args:
            channel: Slack channel ID or name
            timestamp: Message timestamp
            name: Emoji name (without colons, e.g., "thumbsup")

        Returns:
            Enhanced reaction addition result
        """
        try:
            self.logger.log_info(
                f"Adding reaction '{name}' to message in {channel}",
                {"timestamp": timestamp}
            )

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "add_reaction",
                    Exception("Slack client not available"),
                    {
                        "channel": channel,
                        "timestamp": timestamp,
                        "reaction": name,
                        "reaction_skipped": True,
                    }
                )

            client = await self._initialize_client()
            result = await client.add_reaction(channel, timestamp, name)

            enhanced_result = self._create_enhanced_result(
                result,
                "add_reaction",
                channel=channel,
                reaction=name,
            )

            return enhanced_result

        except Exception as e:
            self.logger.log_error(f"Failed to add reaction '{name}'", e)
            return self._handle_graceful_degradation(
                "add_reaction",
                e,
                {
                    "channel": channel,
                    "timestamp": timestamp,
                    "reaction": name,
                    "reaction_failed": True,
                }
            )

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        latest: Optional[str] = None,
        oldest: Optional[str] = None,
        include_all_metadata: bool = False,
    ) -> Dict[str, Any]:
        """
        Get channel message history with Manager enhancements.

        Args:
            channel: Slack channel ID or name
            limit: Maximum number of messages to retrieve (max 1000)
            latest: End of time range of messages to include
            oldest: Start of time range of messages to include
            include_all_metadata: Whether to include all message metadata

        Returns:
            Enhanced channel history with Manager metadata
        """
        try:
            self.logger.log_info(f"Getting channel history for {channel}", {"limit": limit})

            # Check if client is available
            if not await self.is_available():
                return self._handle_graceful_degradation(
                    "get_channel_history",
                    Exception("Slack client not available"),
                    {
                        "channel": channel,
                        "messages": [],
                        "has_more": False,
                        "history_unavailable": True,
                    }
                )

            client = await self._initialize_client()
            history = await client.get_channel_history(
                channel, limit, latest, oldest, include_all_metadata
            )

            enhanced_history = self._create_enhanced_result(
                history,
                "get_channel_history",
                channel=channel,
                limit=limit,
            )

            self.logger.log_info(
                f"Retrieved channel history for {channel}",
                {"message_count": len(history.get("messages", []))}
            )

            return enhanced_history

        except Exception as e:
            self.logger.log_error(f"Failed to get channel history for {channel}", e)
            return self._handle_graceful_degradation(
                "get_channel_history",
                e,
                {
                    "channel": channel,
                    "messages": [],
                    "has_more": False,
                    "history_failed": True,
                }
            )

    async def send_workflow_summary(
        self,
        channel_id: str,
        workflow_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send workflow summary notification to Slack.

        Args:
            channel_id: Slack channel ID or name
            workflow_summary: Workflow summary data

        Returns:
            Summary notification result
        """
        try:
            database_name = workflow_summary.get("database_name", "Unknown")
            duration = workflow_summary.get("duration", 0)
            success = workflow_summary.get("success", False)

            # Create summary message
            status_emoji = "✅" if success else "❌"
            status_text = "Completed Successfully" if success else "Failed"

            message_parts = [
                f"{status_emoji} **Database Decommissioning Workflow {status_text}**",
                "",
                f"**Database:** {database_name}",
                f"**Duration:** {duration:.1f} seconds",
                f"**Status:** {status_text}",
            ]

            # Add workflow metrics if available
            if "metrics" in workflow_summary:
                metrics = workflow_summary["metrics"]
                message_parts.extend([
                    "",
                    "**Metrics:**",
                    f"• Repositories Processed: {metrics.get('repositories_processed', 0)}",
                    f"• Files Modified: {metrics.get('files_modified', 0)}",
                    f"• Total Files: {metrics.get('total_files', 0)}",
                ])

            # Add tenant context
            if self.tenant_id:
                message_parts.append(f"• Tenant: {self.tenant_id}")

            message_text = "\n".join(message_parts)

            return await self.post_message(channel_id, message_text)

        except Exception as e:
            self.logger.log_error("Failed to send workflow summary", e)
            return self._handle_graceful_degradation(
                "send_workflow_summary",
                e,
                {
                    "channel": channel_id,
                    "summary_failed": True,
                }
            )


# Legacy compatibility functions for GraphMCP integration
async def create_slack_client(
    config_path: str | Path,
    tenant_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> SlackClientWrapper:
    """
    Factory function to create Slack client wrapper.

    Args:
        config_path: Path to MCP configuration file
        tenant_id: Optional tenant identifier
        workflow_id: Optional workflow identifier

    Returns:
        Initialized Slack client wrapper
    """
    return SlackClientWrapper(config_path, tenant_id, workflow_id)


async def post_message_with_fallback(
    slack_client: SlackClientWrapper,
    channel_id: str,
    message: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Post message with graceful fallback.

    Args:
        slack_client: Slack client wrapper instance
        channel_id: Slack channel ID
        message: Message to post
        **kwargs: Additional message parameters

    Returns:
        Message posting result with fallback handling
    """
    try:
        return await slack_client.post_message(channel_id, message, **kwargs)
    except Exception as e:
        return {
            "success": False,
            "channel": channel_id,
            "fallback_mode": True,
            "error": str(e),
            "message_text": message,
        }