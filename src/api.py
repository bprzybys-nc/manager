"""
api.py contains the fastapi server that handles all requests and dispatches
celery taks for incidents whenever needed
"""

from celery import Celery
from fastapi import FastAPI

import src.config as config
from src.database.client import DatabaseClient
from src.modules.chat.router import ChatRoute
from src.modules.cmdb.metadata import CMDBMetadata
from src.modules.incident import IncidentDB, IncidentRoute, QuestionDB
from src.modules.inventory import InventoryDB, InventoryRoute
from src.modules.metrics import MetricsRoute, Prometheus, Storage
from src.modules.task import TaskDB, TaskRoute

app = FastAPI()

celery_app = Celery("incident_manager", broker=config.CELERY_BROKER_URL)


# Initialize the database clients
db_client = DatabaseClient({"uri": config.MONGO_DB_URI})
inventory_db = InventoryDB(db_client.client)
incident_db = IncidentDB(db_client.client)
question_db = QuestionDB(db_client.client)
task_db = TaskDB(db_client.client)

# Initialize the prometheus client
flat_storage = Storage(metrics_dir=config.METRICS_DIR)
prometheus = Prometheus(
    prometheus_url=config.PROMETHEUS_ADDRESS,
    manager_api_address=config.MANAGER_API_ADDRESS,
)

# Initialize the CMDB metadata client
cmdb_metadata = CMDBMetadata(cmdb_api_url=config.CMDB_API_URL)

# Include the routes
app.include_router(InventoryRoute(inventory_db).router, prefix="/inventory")
app.include_router(
    IncidentRoute(incident_db, question_db, task_db, celery_app).router,
    prefix="/incidents",
)
app.include_router(
    MetricsRoute(flat_storage, prometheus, inventory_db).router, prefix="/metrics"
)
app.include_router(TaskRoute(task_db, incident_db, cmdb_metadata).router, prefix="/tasks")
app.include_router(
    ChatRoute(prometheus, incident_db, inventory_db, db_client.client).router, prefix="/chat"
)
