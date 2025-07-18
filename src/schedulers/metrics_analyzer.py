import logging
from typing import Dict

import src.config as config
from src.database.client import DatabaseClient
from src.modules.incident.db import Incident, IncidentDB, Status, Type
from src.modules.inventory.db import Instance, InventoryDB
from src.modules.metrics.prometheus import Prometheus

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class MetricsAnalyzer:
    def __init__(self, incident_db: IncidentDB, prometheus: Prometheus):
        self.incident_db = incident_db
        self.prometheus = prometheus

    def analyze_free_space(self, instance: Instance) -> None:
        # if there is an open or acknowledged incident, skip analysis
        incidents = self.incident_db.get_incidents_by_instance_id(instance.id, type=Type.LOW_FREE_SPACE)
        if any(inc.status in [Status.OPEN, Status.ACKNOWLEDGED] for inc in incidents):
            logger.info("There is an open incident, skipping analysis")

        issues = {}
        for mountpoint, data in self.prometheus.get_disk_usage(instance.id).items():
            threshold_usage = next(
                (
                    t.usage
                    for t in instance.config.thresholds.disk_partitions
                    if t.mountpoint == mountpoint
                ),
                None,
            )

            if threshold_usage and data > threshold_usage:
                issues[mountpoint] = data

        if issues:
            logger.info(f"Free space issues found: {issues} for instance {instance.id} Creating incident")
            self.incident_db.create_incident(Incident(
                instance_id=instance.id,
                status=Status.OPEN,
                type=Type.LOW_FREE_SPACE,
                data=issues,
            ))


if __name__ == "__main__":
    prom = Prometheus(config.PROMETHEUS_ADDRESS)
    db_client = DatabaseClient({"uri": config.MONGO_DB_URI})
    inventory_db = InventoryDB(db_client.client)
    incident_db = IncidentDB(db_client.client)

    metrics_analyzer = MetricsAnalyzer(incident_db, prom)

    for instance in inventory_db.get_instances():
        logger.info(f"Analyzing instance {instance.id}")
        issues = metrics_analyzer.analyze_free_space(instance)
        print(issues)
        if issues:
            logger.info(f"Issues found for instance {instance.id}: {issues}")
            inc = incident_db.create_incident(Incident(
                instance_id=instance.id,
                status=Status.OPEN,
                type=Type.LOW_FREE_SPACE,
                data=issues
            ))
            logger.info(f"Incident ID: {inc.id} created for instance {instance.id}")
        else:
            logger.info(f"No issues found for instance {instance.id}")
