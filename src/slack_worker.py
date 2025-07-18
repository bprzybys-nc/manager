"""
slack worker runs an asyncio loop that handles the slack websocket and receives human in the loop events
"""

import src.config as config

from celery import Celery

from src.database.client import DatabaseClient
from src.integrations.hil.slack import SlackAsyncIntegration
from src.modules.incident import QuestionDB
from src.modules.incident import IncidentDB
from src.modules.task import TaskDB


celery_app = Celery("incident_manager", broker=config.CELERY_BROKER_URL)


db_client = DatabaseClient({"uri": config.MONGO_DB_URI})
question_db = QuestionDB(db_client.client)
incident_db = IncidentDB(db_client.client)
question_db = QuestionDB(db_client.client)
task_db = TaskDB(db_client.client)

slack_async_integration = SlackAsyncIntegration(
    config.SLACK_BOT_TOKEN,
    config.SLACK_CHANNEL_NAME,
    celery_app,
    question_db,
    task_db,
    incident_db,
)
