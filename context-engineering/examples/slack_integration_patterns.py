"""
Slack Integration Patterns - Manager Component Examples

This file demonstrates comprehensive Slack API integration patterns used throughout the
Ovora Manager component, with specific focus on the sophisticated patterns from
db_incident_assistant and other production implementations.

Key Patterns Covered:
- Multi-layered Slack integration architecture
- Interactive UI components (buttons, threads)
- Socket Mode real-time communication
- Workflow state integration with LangGraph
- Error handling and graceful degradation
- Correlation ID tracking for user interactions
- Message formatting and rich content
"""

from typing import Dict, Any, List, Optional, Union, Callable, Awaitable
import asyncio
import threading
import logging
import json
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Slack Bolt framework imports
try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.app import App
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    from slack_sdk.errors import SlackApiError
except ImportError:
    # Fallback for when dependencies are not available
    class AsyncApp:
        pass
    class App:
        pass
    class AsyncSocketModeHandler:
        pass
    class SlackApiError(Exception):
        pass

# Configure logging
logger = logging.getLogger(__name__)

class SlackFormatting(Enum):
    """Slack message formatting options."""
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    CODE_BLOCK = "code_block"
    STRIKETHROUGH = "strikethrough"

class SlackMessageType(Enum):
    """Types of Slack messages in Manager component."""
    STATUS_UPDATE = "status_update"
    INTERACTIVE_QUESTION = "interactive_question"
    INCIDENT_ALERT = "incident_alert"
    WORKFLOW_NOTIFICATION = "workflow_notification"
    COMMAND_APPROVAL = "command_approval"
    THREAD_UPDATE = "thread_update"

@dataclass
class SlackResponse:
    """Standard Slack API response structure."""
    success: bool
    thread_id: Optional[str] = None
    message_ts: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SlackInteractionContext:
    """Context for Slack interactive components."""
    correlation_id: str
    user_id: str
    thread_ts: Optional[str] = None
    channel_id: Optional[str] = None
    workflow_context: Optional[Dict[str, Any]] = None

# Core Slack Integration Patterns

class BaseSlackIntegration:
    """
    Base pattern for Slack integrations in Manager component.
    
    Provides common functionality for:
    - Socket Mode connection management
    - Message formatting and sending
    - Interactive component handling
    - Error handling and retry logic
    - Thread management
    
    Based on patterns from:
    - src/integrations/hil/slack/slack.py
    - src/tools/communication/app/slack.py
    - db_incident_assistant implementations
    """
    
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        default_channel: str,
        service_name: str = "BaseSlack"
    ):
        self.bot_token = bot_token
        self.app_token = app_token
        self.default_channel = default_channel
        self.service_name = service_name
        
        # Initialize Slack applications
        self.app = AsyncApp(token=bot_token)
        self.sync_app = App(token=bot_token)
        self.handler = AsyncSocketModeHandler(self.app, app_token)
        
        # State management
        self.active_threads: Dict[str, str] = {}  # workflow_id -> thread_ts
        self.pending_interactions: Dict[str, SlackInteractionContext] = {}
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack event handlers."""
        
        # Button interaction handlers
        @self.app.action("hilyes")
        async def handle_yes_button(ack, body, client):
            await self._handle_button_interaction(ack, body, client, "yes")
        
        @self.app.action("hilno")
        async def handle_no_button(ack, body, client):
            await self._handle_button_interaction(ack, body, client, "no")
        
        # Generic action handler for extensibility
        @self.app.action("custom_action")
        async def handle_custom_action(ack, body, client):
            await self._handle_custom_action(ack, body, client)
    
    async def _handle_button_interaction(self, ack, body, client, response_value: str):
        """Handle yes/no button interactions with correlation tracking."""
        await ack()
        
        def process_interaction():
            try:
                # Extract correlation ID and context
                block_id = body.get("actions", [{}])[0].get("block_id")
                user_id = body["user"]["id"]
                channel_id = body["channel"]["id"]
                
                if not block_id:
                    logger.error("No block_id found in button interaction")
                    return
                
                # Get interaction context
                context = self.pending_interactions.get(block_id)
                if not context:
                    logger.warning(f"No pending interaction found for correlation_id: {block_id}")
                    return
                
                # Process the response
                self._process_user_response(context, response_value, user_id)
                
                # Update the message to show response
                self._update_button_message(client, body, response_value)
                
                # Remove from pending interactions
                del self.pending_interactions[block_id]
                
            except Exception as e:
                logger.error(f"Error processing button interaction: {e}")
        
        # Process in background thread to avoid blocking
        threading.Thread(target=process_interaction).start()
    
    async def _handle_custom_action(self, ack, body, client):
        """Handle custom Slack actions - override in subclasses."""
        await ack()
        logger.info(f"Custom action received: {body}")
    
    def _process_user_response(
        self,
        context: SlackInteractionContext,
        response: str,
        user_id: str
    ):
        """Process user response - override in subclasses."""
        logger.info(f"User {user_id} responded '{response}' to {context.correlation_id}")
    
    def _update_button_message(self, client, body, response_value: str):
        """Update button message to show user response."""
        try:
            response_emoji = "✅" if response_value == "yes" else "❌"
            response_text = "Yes" if response_value == "yes" else "No"
            
            # Get original message
            message = body["message"]
            
            # Update blocks to show response
            updated_blocks = []
            for block in message["blocks"]:
                if block["type"] == "actions":
                    # Replace action block with response
                    updated_blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{response_emoji} *Response: {response_text}*"
                        }
                    })
                else:
                    updated_blocks.append(block)
            
            # Update the message
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                blocks=updated_blocks,
                text=f"Response: {response_text}"
            )
            
        except Exception as e:
            logger.error(f"Error updating button message: {e}")
    
    async def connect(self):
        """Connect to Slack via Socket Mode."""
        try:
            await self.handler.connect_async()
            logger.info(f"{self.service_name} connected to Slack")
        except Exception as e:
            logger.error(f"Failed to connect {self.service_name} to Slack: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Slack."""
        try:
            await self.handler.disconnect_async()
            logger.info(f"{self.service_name} disconnected from Slack")
        except Exception as e:
            logger.error(f"Error disconnecting {self.service_name} from Slack: {e}")
    
    def format_message(self, text: str, formatting: SlackFormatting = None) -> str:
        """Format message text with Slack markdown."""
        if not formatting:
            return text
        
        if formatting == SlackFormatting.BOLD:
            return f"*{text}*"
        elif formatting == SlackFormatting.ITALIC:
            return f"_{text}_"
        elif formatting == SlackFormatting.CODE:
            return f"`{text}`"
        elif formatting == SlackFormatting.CODE_BLOCK:
            return f"```\n{text}\n```"
        elif formatting == SlackFormatting.STRIKETHROUGH:
            return f"~{text}~"
        
        return text
    
    def send_message(
        self,
        text: str,
        channel: str = None,
        thread_ts: str = None,
        formatting: SlackFormatting = None,
        blocks: List[Dict] = None
    ) -> SlackResponse:
        """Send a message to Slack channel."""
        try:
            formatted_text = self.format_message(text, formatting)
            
            response = self.sync_app.client.chat_postMessage(
                channel=channel or self.default_channel,
                text=formatted_text,
                thread_ts=thread_ts,
                blocks=blocks
            )
            
            return SlackResponse(
                success=True,
                thread_id=response["ts"],
                message_ts=response["ts"],
                metadata={"channel": response["channel"]}
            )
            
        except SlackApiError as e:
            logger.error(f"Slack API error sending message: {e}")
            return SlackResponse(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return SlackResponse(
                success=False,
                error=str(e)
            )
    
    def create_thread(
        self,
        initial_message: str,
        channel: str = None,
        formatting: SlackFormatting = None
    ) -> SlackResponse:
        """Create a new thread with initial message."""
        return self.send_message(
            text=initial_message,
            channel=channel,
            formatting=formatting
        )
    
    def send_interactive_question(
        self,
        question: str,
        correlation_id: str,
        channel: str = None,
        thread_ts: str = None,
        custom_actions: List[Dict] = None
    ) -> SlackResponse:
        """Send interactive question with yes/no buttons."""
        try:
            # Create button blocks
            if custom_actions:
                action_elements = custom_actions
            else:
                action_elements = [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Yes"},
                        "style": "primary",
                        "value": "yes",
                        "action_id": "hilyes",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "No"},
                        "style": "danger",
                        "value": "no",
                        "action_id": "hilno",
                    },
                ]
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": question
                    }
                },
                {
                    "type": "actions",
                    "block_id": correlation_id,
                    "elements": action_elements,
                },
            ]
            
            response = self.send_message(
                text=question,
                channel=channel,
                thread_ts=thread_ts,
                blocks=blocks
            )
            
            if response.success:
                # Store interaction context
                self.pending_interactions[correlation_id] = SlackInteractionContext(
                    correlation_id=correlation_id,
                    user_id="",  # Will be filled when interaction occurs
                    thread_ts=thread_ts,
                    channel_id=channel or self.default_channel
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending interactive question: {e}")
            return SlackResponse(
                success=False,
                error=str(e)
            )

# Incident Assistant Slack Integration Pattern
class IncidentAssistantSlackIntegration(BaseSlackIntegration):
    """
    Specialized Slack integration for incident management workflows.
    
    Based on the sophisticated patterns from:
    - src/usecases/db_incident_assistant/app/main.py
    - OutboundCommunication class implementation
    - LangGraph workflow integration patterns
    """
    
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        default_channel: str,
        workflow_callback: Callable[[str, str, str], Awaitable[None]] = None
    ):
        super().__init__(bot_token, app_token, default_channel, "IncidentAssistant")
        self.workflow_callback = workflow_callback
        self.incident_threads: Dict[str, str] = {}  # incident_id -> thread_ts
    
    def _process_user_response(
        self,
        context: SlackInteractionContext,
        response: str,
        user_id: str
    ):
        """Process user response and trigger workflow continuation."""
        logger.info(f"Incident workflow response: {context.correlation_id} -> {response}")
        
        # Parse correlation ID to extract incident and command info
        try:
            parts = context.correlation_id.split('_')
            if len(parts) >= 3:
                incident_id = parts[0]
                action_type = parts[1]  # e.g., 'cmd', 'approval'
                action_id = parts[2]
                
                # Trigger workflow callback if provided
                if self.workflow_callback:
                    asyncio.create_task(
                        self.workflow_callback(incident_id, action_id, response)
                    )
                
                logger.info(f"Processed incident {incident_id} action {action_type}:{action_id} = {response}")
            else:
                logger.warning(f"Invalid correlation ID format: {context.correlation_id}")
                
        except Exception as e:
            logger.error(f"Error processing incident workflow response: {e}")
    
    def create_incident_thread(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: str = "medium"
    ) -> SlackResponse:
        """Create dedicated thread for incident tracking."""
        
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "🔸",
            "low": "ℹ️"
        }.get(severity.lower(), "🔸")
        
        initial_message = f"{severity_emoji} *New Incident: {title}*\n\n{description}"
        
        response = self.create_thread(
            initial_message=initial_message,
            formatting=None  # Already formatted with markdown
        )
        
        if response.success:
            self.incident_threads[incident_id] = response.thread_id
            logger.info(f"Created incident thread for {incident_id}: {response.thread_id}")
        
        return response
    
    def send_incident_update(
        self,
        incident_id: str,
        message: str,
        formatting: SlackFormatting = None
    ) -> SlackResponse:
        """Send update to incident thread."""
        
        thread_ts = self.incident_threads.get(incident_id)
        if not thread_ts:
            logger.warning(f"No thread found for incident {incident_id}")
            return SlackResponse(success=False, error="No thread found for incident")
        
        return self.send_message(
            text=message,
            thread_ts=thread_ts,
            formatting=formatting
        )
    
    def request_command_approval(
        self,
        incident_id: str,
        command_id: str,
        command_description: str,
        command_text: str
    ) -> SlackResponse:
        """Request approval for incident remediation command."""
        
        correlation_id = f"{incident_id}_cmd_{command_id}"
        
        question_text = f"""*Command Approval Required*
        
Description: {command_description}

Command to execute:
```
{command_text}
```

Do you approve executing this command?"""
        
        thread_ts = self.incident_threads.get(incident_id)
        
        return self.send_interactive_question(
            question=question_text,
            correlation_id=correlation_id,
            thread_ts=thread_ts
        )
    
    def send_command_results(
        self,
        incident_id: str,
        command_description: str,
        results: str,
        success: bool = True
    ) -> SlackResponse:
        """Send command execution results to incident thread."""
        
        status_emoji = "✅" if success else "❌"
        status_text = "Success" if success else "Failed"
        
        message = f"""{status_emoji} *Command {status_text}: {command_description}*

Results:
```
{results}
```"""
        
        return self.send_incident_update(
            incident_id=incident_id,
            message=message
        )

# Database Decommissioning Slack Integration Pattern
class DatabaseDecommissioningSlackIntegration(BaseSlackIntegration):
    """
    Specialized Slack integration for database decommissioning workflows.
    
    Based on patterns from:
    - src/usecases/database_decommissioning/app/clients/slack_client.py
    - GraphMCP workflow integration
    - Tenant-aware messaging patterns
    """
    
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        default_channel: str,
        tenant_config: Dict[str, Any] = None
    ):
        super().__init__(bot_token, app_token, default_channel, "DatabaseDecommissioning")
        self.tenant_config = tenant_config or {}
        self.workflow_threads: Dict[str, str] = {}  # workflow_id -> thread_ts
    
    def send_decommissioning_notification(
        self,
        workflow_id: str,
        database_name: str,
        tenant: str,
        phase: str,
        details: Dict[str, Any] = None
    ) -> SlackResponse:
        """Send database decommissioning phase notification."""
        
        phase_emojis = {
            "discovery": "🔍",
            "analysis": "📊",
            "validation": "✅",
            "backup": "💾",
            "decommission": "🗂️",
            "cleanup": "🧹",
            "completion": "🎉"
        }
        
        emoji = phase_emojis.get(phase.lower(), "📋")
        
        # Create rich notification blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Database Decommissioning - {phase.title()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Database:* {database_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Tenant:* {tenant}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Phase:* {phase.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Workflow ID:* {workflow_id}"
                    }
                ]
            }
        ]
        
        # Add details if provided
        if details:
            details_text = "\n".join([f"• {k}: {v}" for k, v in details.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{details_text}"
                }
            })
        
        thread_ts = self.workflow_threads.get(workflow_id)
        
        response = self.send_message(
            text=f"{emoji} Database Decommissioning - {phase.title()}: {database_name}",
            thread_ts=thread_ts,
            blocks=blocks
        )
        
        # Store thread if this is the first message
        if response.success and not thread_ts:
            self.workflow_threads[workflow_id] = response.thread_id
        
        return response
    
    def request_decommissioning_approval(
        self,
        workflow_id: str,
        database_name: str,
        impact_assessment: Dict[str, Any],
        backup_info: Dict[str, Any] = None
    ) -> SlackResponse:
        """Request approval for database decommissioning."""
        
        correlation_id = f"{workflow_id}_approval_decommission"
        
        # Build approval message
        message_parts = [
            f"*🚨 FINAL APPROVAL REQUIRED 🚨*",
            f"",
            f"Database: *{database_name}*",
            f"Workflow: {workflow_id}",
            f"",
            f"*Impact Assessment:*"
        ]
        
        for key, value in impact_assessment.items():
            message_parts.append(f"• {key}: {value}")
        
        if backup_info:
            message_parts.extend([
                f"",
                f"*Backup Information:*"
            ])
            for key, value in backup_info.items():
                message_parts.append(f"• {key}: {value}")
        
        message_parts.extend([
            f"",
            f"⚠️ *This action is IRREVERSIBLE* ⚠️",
            f"",
            f"Do you approve proceeding with decommissioning?"
        ])
        
        question_text = "\n".join(message_parts)
        
        thread_ts = self.workflow_threads.get(workflow_id)
        
        return self.send_interactive_question(
            question=question_text,
            correlation_id=correlation_id,
            thread_ts=thread_ts
        )

# Multi-Client Orchestration Pattern
class OrchestatedSlackIntegration:
    """
    Pattern for orchestrating multiple Slack integrations within workflows.
    
    Used in GraphMCP workflows where multiple MCP clients coordinate
    Slack operations for complex multi-step processes.
    """
    
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        default_channel: str
    ):
        self.bot_token = bot_token
        self.app_token = app_token
        self.default_channel = default_channel
        
        # Initialize specialized integrations
        self.incident_integration = IncidentAssistantSlackIntegration(
            bot_token, app_token, default_channel
        )
        self.decommissioning_integration = DatabaseDecommissioningSlackIntegration(
            bot_token, app_token, default_channel
        )
        
        # Shared state across integrations
        self.workflow_contexts: Dict[str, Dict[str, Any]] = {}
    
    async def start_orchestrated_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        initial_context: Dict[str, Any]
    ):
        """Start coordinated workflow across multiple Slack integrations."""
        
        # Store workflow context
        self.workflow_contexts[workflow_id] = {
            "type": workflow_type,
            "context": initial_context,
            "started_at": datetime.now().isoformat(),
            "integrations": []
        }
        
        # Connect all integrations
        await self.incident_integration.connect()
        await self.decommissioning_integration.connect()
        
        logger.info(f"Started orchestrated workflow {workflow_id} of type {workflow_type}")
    
    async def stop_orchestrated_workflow(self, workflow_id: str):
        """Stop coordinated workflow and cleanup resources."""
        
        if workflow_id in self.workflow_contexts:
            del self.workflow_contexts[workflow_id]
        
        # Disconnect integrations
        await self.incident_integration.disconnect()
        await self.decommissioning_integration.disconnect()
        
        logger.info(f"Stopped orchestrated workflow {workflow_id}")
    
    def get_integration_for_workflow(self, workflow_type: str) -> BaseSlackIntegration:
        """Get appropriate Slack integration for workflow type."""
        
        if workflow_type in ["incident", "incident_analysis", "db_incident"]:
            return self.incident_integration
        elif workflow_type in ["decommissioning", "db_decommission", "cleanup"]:
            return self.decommissioning_integration
        else:
            # Default to incident integration
            return self.incident_integration

# Connection Management Pattern
@asynccontextmanager
async def slack_connection_manager(
    bot_token: str,
    app_token: str,
    default_channel: str,
    service_name: str = "SlackService"
):
    """
    Context manager for Slack connection lifecycle management.
    
    Ensures proper connection setup and cleanup for Slack integrations.
    Based on patterns from db_incident_assistant FastAPI lifespan management.
    """
    
    integration = BaseSlackIntegration(bot_token, app_token, default_channel, service_name)
    
    try:
        await integration.connect()
        logger.info(f"Slack connection established for {service_name}")
        yield integration
    except Exception as e:
        logger.error(f"Failed to establish Slack connection for {service_name}: {e}")
        raise
    finally:
        try:
            await integration.disconnect()
            logger.info(f"Slack connection closed for {service_name}")
        except Exception as e:
            logger.error(f"Error closing Slack connection for {service_name}: {e}")

# Configuration Pattern
class SlackIntegrationConfig:
    """
    Configuration management for Slack integrations.
    
    Centralizes environment variable handling and service configuration
    following Manager component configuration patterns.
    """
    
    def __init__(
        self,
        bot_token: str = None,
        app_token: str = None,
        channel: str = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        import os
        
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.app_token = app_token or os.getenv("SLACK_APP_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL", "project-harbinger")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration values."""
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required")
        if not self.app_token:
            raise ValueError("SLACK_APP_TOKEN is required")
        if not self.channel:
            raise ValueError("SLACK_CHANNEL is required")
    
    def create_incident_integration(
        self,
        workflow_callback: Callable[[str, str, str], Awaitable[None]] = None
    ) -> IncidentAssistantSlackIntegration:
        """Create incident assistant Slack integration."""
        return IncidentAssistantSlackIntegration(
            self.bot_token,
            self.app_token,
            self.channel,
            workflow_callback
        )
    
    def create_decommissioning_integration(
        self,
        tenant_config: Dict[str, Any] = None
    ) -> DatabaseDecommissioningSlackIntegration:
        """Create database decommissioning Slack integration."""
        return DatabaseDecommissioningSlackIntegration(
            self.bot_token,
            self.app_token,
            self.channel,
            tenant_config
        )

# Example Usage Patterns
async def example_incident_workflow():
    """Example of incident workflow with Slack integration."""
    
    config = SlackIntegrationConfig()
    
    async def workflow_callback(incident_id: str, action_id: str, response: str):
        """Handle workflow responses from Slack interactions."""
        logger.info(f"Workflow callback: {incident_id}/{action_id} = {response}")
        # Here you would integrate with LangGraph to continue workflow
    
    integration = config.create_incident_integration(workflow_callback)
    
    async with slack_connection_manager(
        config.bot_token,
        config.app_token,
        config.channel,
        "IncidentExample"
    ):
        # Create incident thread
        incident_id = "INC-2024-001"
        response = integration.create_incident_thread(
            incident_id=incident_id,
            title="Database Connection Pool Exhausted",
            description="Application unable to connect to database",
            severity="high"
        )
        
        if response.success:
            # Send status update
            integration.send_incident_update(
                incident_id=incident_id,
                message="Analyzing connection pool metrics...",
                formatting=SlackFormatting.ITALIC
            )
            
            # Request command approval
            integration.request_command_approval(
                incident_id=incident_id,
                command_id="restart_pool",
                command_description="Restart database connection pool",
                command_text="systemctl restart db-pool"
            )
            
            # Wait for user interaction (handled by workflow_callback)
            await asyncio.sleep(5)
            
            # Send results
            integration.send_command_results(
                incident_id=incident_id,
                command_description="Restart database connection pool",
                results="Connection pool restarted successfully. Active connections: 15/100",
                success=True
            )

async def example_decommissioning_workflow():
    """Example of database decommissioning workflow with Slack integration."""
    
    config = SlackIntegrationConfig()
    integration = config.create_decommissioning_integration()
    
    async with slack_connection_manager(
        config.bot_token,
        config.app_token,
        config.channel,
        "DecommissioningExample"
    ):
        workflow_id = "DECOMM-2024-001"
        
        # Send discovery notification
        integration.send_decommissioning_notification(
            workflow_id=workflow_id,
            database_name="legacy_reporting_db",
            tenant="acme_corp",
            phase="discovery",
            details={
                "Size": "125 GB",
                "Last Access": "2023-11-15",
                "Dependencies": "2 applications identified"
            }
        )
        
        # Send analysis results
        integration.send_decommissioning_notification(
            workflow_id=workflow_id,
            database_name="legacy_reporting_db",
            tenant="acme_corp",
            phase="analysis",
            details={
                "Risk Level": "Low",
                "Business Impact": "Minimal",
                "Technical Dependencies": "None active"
            }
        )
        
        # Request final approval
        integration.request_decommissioning_approval(
            workflow_id=workflow_id,
            database_name="legacy_reporting_db",
            impact_assessment={
                "Applications": "0 active dependencies",
                "Data Criticality": "Low (archived reports)",
                "Recovery Time": "Not applicable",
                "Business Risk": "Minimal"
            },
            backup_info={
                "Backup Status": "Completed",
                "Backup Size": "125 GB",
                "Retention": "7 years",
                "Location": "S3://backups/legacy_reporting_db"
            }
        )

if __name__ == "__main__":
    # Example usage
    asyncio.run(example_incident_workflow())