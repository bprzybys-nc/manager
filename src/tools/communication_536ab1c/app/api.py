import certifi
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi import Request
from pymongo import MongoClient
from pydantic import BaseModel


from src.modules.incident import TaskDB
from src.tools.communication.app.slack import Slack, SlackFormatting


connection_string = os.environ.get('MONGODB_URI')
db_client = MongoClient(connection_string, tlsCAFile=certifi.where())
task_db = TaskDB(db_client)


slack = Slack(os.getenv("SLACK_BOT_TOKEN"), os.getenv("SLACK_APP_TOKEN"),os.getenv("SLACK_CHANNEL"),task_db)

class CommandQuestionRequest(BaseModel):
    thread_id: Optional[str] = None
    command_id: Optional[str] = None
    question: Optional[str] = None

@asynccontextmanager
async def slack_conn(app: FastAPI):
    print(f"Connecting to Slack: {slack.get_handler()}")
    try:
        await slack.get_handler().connect_async()
        yield
        await slack.get_handler().disconnect_async()
    except Exception as e:
        print(f"Error connecting to Slack: {e}")

app = FastAPI(lifespan=slack_conn)

@app.post("/slack/events")
async def endpoint(req: Request):
    print(f"Received Slack event: {await req.body()}")
    return await slack.get_handler().handle(req)


@app.post("/messages/")
async def send_message(payload: dict):
    print(f"Received message: {payload}")
    try:
        if 'formatting' in payload:
            formatting = SlackFormatting(payload["formatting"])
        else:
            formatting = None
        if 'thread_id' in payload:
            thread_id = payload["thread_id"]
            slack.send_message(thread_id, payload["message"], formatting)
        else:
            thread_id = slack.create_thread(payload["message"], formatting)
        print(f"Message sent successfully, thread_id: {thread_id}")
        return {"message": "Message sent successfully", "thread_id": thread_id}
    except Exception as e:
        print(f"Error sending message: {e}")
        return {"message": f"Error sending message: {e}"}

@app.post("/questions/")
async def send_question(payload: CommandQuestionRequest):
    print(f"Sending question: {payload}")
    try:
        thread_id = payload.thread_id
        question = payload.question
        command_id = payload.command_id
        slack.send_question(thread_id, question, command_id)
        return {"message": "Question sent successfully", "thread_id": thread_id}
    except Exception as e:
        print(f"Error sending question: {e}")
        return {"message": f"Error sending question: {e}"}



