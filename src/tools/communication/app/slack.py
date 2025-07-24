import os
import sys
import uuid
from enum import Enum
from typing import Optional, List
from uuid import UUID
from uuid import uuid4

import requests
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app import App
from slack_bolt.async_app import AsyncAck, AsyncApp

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from src.tools.communication.app.communication_channel import CommunicationsChannel
from src.modules.task.db import Task, CommandType, Type, State, TaskDB


class SlackFormatting(Enum):
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    CODE_BLOCK = "code_block"

class OutboundCommunication():

    def __init__(self):
        self.db_assistant_response_endpoint = os.getenv("DB_INCIDENT_ASSISTANT_RESPONSE_ENDPOINT")

    def send_confirmation(self,correlation_id: str,approved: bool):
        print(f"Sending confirmation for {correlation_id}")
        response = requests.post(self.db_assistant_response_endpoint, json={"correlation_id": correlation_id, "approved": approved})
        print(f"Response: {response}")

class Slack(CommunicationsChannel):

    def __init__(self, bot_token: str, app_token: str, channel: str,task_db: TaskDB):
        self.app = AsyncApp(token=bot_token)
        self.sync_app = App(token=bot_token)
        self.app_token = app_token
        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        self.channel = channel
        self.app.action("hilyes")(self.action_yes)
        self.app.action("hilno")(self.action_no)
        self.task_db = task_db
        self.outbound_communication = OutboundCommunication()

    def get_channel_type(self) -> str:
        return "slack"
    
    def create_thread(self, message: str, formatting: Optional[SlackFormatting] = None) -> str:
        formatted_message = self._format_message(message, formatting)
        print(f"Formatted message: {formatted_message}")
        response = self.sync_app.client.chat_postMessage(
            channel=self.channel,
            markdown_text=formatted_message,
            as_user=True,
        )
        return response["ts"]

    def send_message(self, thread_id: str, message: str, formatting: Optional[SlackFormatting] = None) -> str:
        formatted_message = self._format_message(message, formatting)
        print(f"Thread ID: {thread_id}")
        print(f"Formatted message: {formatted_message}")
        response = self.sync_app.client.chat_postMessage(
            channel=self.channel,
            markdown_text=formatted_message,
            thread_ts=thread_id,
            as_user=True,
        )
        return response["ts"]

    def send_question(self, thread_id: str, question_text: str, correlation_id: str) -> str:
        print(f"Yesno question: {question_text} {correlation_id}")
        try:
            response = self.sync_app.client.chat_postMessage(
                channel=self.channel,
                thread_ts=thread_id,
                as_user=True,
                blocks=[
                    {"type": "section", "text": {"type": "mrkdwn", "text": question_text}},
                    {
                        "type": "actions",
                        "block_id": str(correlation_id),
                        "elements": [
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
                        ],
                    },
                ],
            )
        except Exception as e:
            print(f"Error sending question: {e}")
            raise

    async def action_yes(self, ack: AsyncAck, body, client):
        print(f"Yes action: {body}")
        await ack()
        correlation_id = body["actions"][0]["block_id"]
        import threading
        import logging

        def req(correlation_id):
            try:
                logging.info(f"Sending APPROVED confirmation for {correlation_id}")
                self.outbound_communication.send_confirmation(correlation_id,True)
                # Update UI to show response was received
                blocks = body["message"]["blocks"]
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "✅ *Response recorded: YES*"}
                })
                self.sync_app.client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    blocks=blocks
                )
            except Exception as e:
                logging.error(f"Error sending YES for {correlation_id}: {e}")

        threading.Thread(target=req, args=(correlation_id,)).start()

    async def action_no(self, ack: AsyncAck, body, client):
        print(f"No action: {body}")
        await ack()
        correlation_id = body["actions"][0]["block_id"]
        import threading
        import logging

        def req(correlation_id):
            try:
                logging.info(f"Sending REJECTED confirmation for {correlation_id}")
                self.outbound_communication.send_confirmation(correlation_id,False)
                # Update UI to show response was received
                blocks = body["message"]["blocks"]
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "❌ *Response recorded: NO*"}
                })
                self.sync_app.client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    blocks=blocks
                )
            except Exception as e:
                logging.error(f"Error sending NO for {correlation_id}: {e}")

        threading.Thread(target=req, args=(correlation_id,)).start()

    def get_handler(self) -> AsyncSocketModeHandler:
        return self.handler

    def remove_newline_at_end(self, message: str) -> str:
        while len(message) > 0 and message[-1] == "\n":
            message = message[:-1]
        return message

    def _format_message(self, message: str, formatting: Optional[SlackFormatting] = None) -> str:
        message = self.remove_newline_at_end(message)
        if formatting is None:
            return message
        if formatting == SlackFormatting.BOLD:
            return f"**{message}**"
        elif formatting == SlackFormatting.ITALIC:
            return f"_{message}_"
        elif formatting == SlackFormatting.CODE:
            return f"`{message}`"
        elif formatting == SlackFormatting.CODE_BLOCK:
            return f"```{message}"
        
