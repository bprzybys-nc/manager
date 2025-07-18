import os
from datetime import timedelta

# The address of the Prometheus server.
PROMETHEUS_ADDRESS = os.getenv("PROMETHEUS_ADDRESS", "http://localhost:9090")

# The address of the manager API. This is used to create targets for Prometheus.
MANAGER_API_ADDRESS = os.getenv("MANAGER_API_ADDRESS", "localhost:9123")

# The address of the CMDB API. This is used to fetch metadata from the CMDB.
CMDB_API_URL = os.getenv("CMDB_API_URL", "http://localhost:8001")

# The directory where the metrics are stored. This is used to store the metrics data that is fetched from Prometheus.
METRICS_DIR = os.getenv("METRICS_DIR", "metrics")

# The MongoDB database URI.
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017")

# The name of the database and collection used to store the langgraph checkpoints.
SYSAIDMIN_DB_NAME = os.getenv("SYSAIDMIN_DB_NAME", "sysaidmin")
CHECKPOINT_COLLECTION_NAME = os.getenv("CHECKPOINT_COLLECTION_NAME", "checkpoints")

# The triggers for the metrics analyzer. This is used to configure the triggers for scheduled worker tasks.
SCHEDULER_TRIGGERS = {
    "analyze_free_space": timedelta(seconds=60),
    "threshold_setter": timedelta(days=1),
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost")
CELERY_APP_NAME = "incident_manager"

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_CHANNEL_NAME = "project-harbinger"
