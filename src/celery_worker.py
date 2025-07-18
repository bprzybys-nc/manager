"""
app.py contains a celery worker that recieves incident tasks from the API, executes incident assistant
and schedules tasks for maintenance and analysis tasks

for now this also handles the slack websocket until we move it to a separate worker
"""

from contextlib import contextmanager

from celery import Celery
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import src.config as config
from src.integrations.hil.slack import SlackIntegration
from src.modules.incident.assistant import IncidentAssistant
from src.modules.incident.db import IncidentDB
from src.modules.inventory.db import InventoryDB
from src.modules.metrics.prometheus import Prometheus
from src.schedulers.metrics_analyzer import MetricsAnalyzer
from src.schedulers.threshold_setter import ThresholdSetter

hil_integration = SlackIntegration(config.SLACK_BOT_TOKEN, config.SLACK_CHANNEL_NAME)
prometheus = Prometheus(config.PROMETHEUS_ADDRESS, config.MANAGER_API_ADDRESS)


app = Celery(config.CELERY_APP_NAME, broker=config.CELERY_BROKER_URL)
app.conf.beat_schedule = {
    "analyze_free_space": {
        "task": "scheduler.analyze_free_space",
        "schedule": config.SCHEDULER_TRIGGERS["analyze_free_space"],
    },
    "set_thresholds": {
        "task": "scheduler.set_thresholds",
        "schedule": config.SCHEDULER_TRIGGERS["threshold_setter"],
    },
}


# Helper functions

@contextmanager
def get_mongo_client(mongo_uri):
    """
    Context manager for MongoDB connection.
    """
    client = MongoClient(mongo_uri)
    try:
        client.is_mongos
        yield client
    except PyMongoError as e:
        raise Exception(f"Could not connect to MongoDB: {e}")
    finally:
        client.close()


# Tasks from the API

@app.task(name="run_incident_assistant")
def run_incident_assistant(
    incident_id: str, task_ids: list[str], q_ids: list[str] = []
):
    """
    Run the incident assistant for a given incident.
    """

    with get_mongo_client(config.MONGO_DB_URI) as client:
        incident_assistant = IncidentAssistant(client, hil_integration)

        incident_assistant.run(incident_id, task_ids, q_ids)


# Tasks from the scheduler

@app.task(name="scheduler.analyze_free_space")
def analyze_free_space():
    """
    Analyze free space on all instances and create incidents if necessary.
    """

    with get_mongo_client(config.MONGO_DB_URI) as client:
        inventory_db = InventoryDB(client)

        metric_analyzer = MetricsAnalyzer(IncidentDB(client), prometheus)

        for instance in inventory_db.get_instances():
            metric_analyzer.analyze_free_space(instance)


@app.task(name="scheduler.set_thresholds")
def set_thresholds():
    """
    Set thresholds for all instances.
    """

    with get_mongo_client(config.MONGO_DB_URI) as client:
        inventory_db = InventoryDB(client)

        threshold_setter = ThresholdSetter(prometheus, inventory_db)

        for instance in inventory_db.get_instances():
            threshold_setter.run_thresholds_analysis(instance.id)
