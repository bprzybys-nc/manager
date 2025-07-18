import logging
from uuid import UUID
from typing import Literal

from celery import Celery
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app import App
from slack_bolt.async_app import AsyncAck, AsyncApp

from src.integrations.hil.hil import HILIntegration
from src.modules.incident import QuestionDB
from src.modules.task import TaskDB
from src.modules.task.db import State
from src.modules.incident import IncidentDB


class SlackIntegration(HILIntegration):
    """
    SlackIntegration can be used to send messages to the applications slack channel
    """

    bot_token: str
    channel: str

    def __init__(self, bot_token: str, channel: str):
        self.app = App(token=bot_token)
        self.channel = channel

    def write_message(self, message: str, thread_id: str = None):
        res = self.app.client.chat_postMessage(
            channel=self.channel,
            text=message,
            thread_ts=thread_id,
            as_user=True,
        )

        return res["ts"]

    def yesno(
        self,
        question: str,
        question_id: UUID,
        thread_id: str,
    ) -> str:
        response = self.app.client.chat_postMessage(
            channel=self.channel,
            thread_ts=thread_id,
            as_user=True,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": question}},
                {
                    "type": "actions",
                    "block_id": str(question_id),
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

        return response["ts"]


class SlackAsyncIntegration:
    """
    Async bolt app that receives yes/no actions from the human in the loop integration
    """

    app: AsyncApp
    channel: str
    task_broker: Celery
    q_db: QuestionDB
    t_db: TaskDB
    incident_db: IncidentDB

    def __init__(
        self,
        bot_token: str,
        channel: str,
        task_broker: Celery,
        question_db: QuestionDB,
        task_db: TaskDB,
        incident_db: IncidentDB,
    ):
        self.app = AsyncApp(token=bot_token)
        self.channel = channel
        self.task_broker = task_broker
        self.q_db = question_db
        self.t_db = task_db
        self.incident_db = incident_db

        self.app.action("hilyes")(self.action_yes)
        self.app.action("hilno")(self.action_no)

    async def action_yes(self, ack: AsyncAck, body, client):
        await ack()
        question_id = body["actions"][0]["block_id"]

        await self.question_answer(question_id, "yes")

    async def action_no(self, ack: AsyncAck, body, client):
        await ack()
        question_id = body["actions"][0]["block_id"]

        await self.question_answer(question_id, "no")

    async def question_answer(self, question_id: str, answer: Literal["yes", "no"]):
        print(f"Received question answer from slack: {question_id}, {answer}")
        question = self.q_db.get_question(question_id)
        question.response = answer
        self.q_db.update_question(question)
        task = self.t_db.get_task(question.task_id)

        if answer == "yes":
            print(f"Updating task {task.id} to approved")
            self.t_db.update_state(task.id, State.APPROVED)
        else:
            print(f"Updating task {task.id} to rejected")
            self.t_db.update_state(task.id, State.REJECTED)

        incident = self.incident_db.get_incident(task.incident_id)

        print(f"Sending taks to worker to process answer: {answer} for task: {task.id}")
        logging.info(
            f"Sending taks to worker to process answer: {answer} for task: {task.id}"
        )

        self.task_broker.send_task(
            "run_incident_assistant", (incident.id, [task.id], [question_id])
        )

        return question.id
