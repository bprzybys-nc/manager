import logging
from datetime import datetime, timedelta
from typing import Dict, List

from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

import src.config as config
from src.database.client import DatabaseClient
from src.llm import llm
from src.modules.inventory.db import InventoryDB, Thresholds
from src.modules.metrics.prometheus import Prometheus

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


THRESHOLD_ANALYSIS_PROMPT = """You are a disk threshold analysis agent. Your task is to analyze disk usage metrics and
set appropriate alert thresholds.

For each instance:
1. Get the metrics using get_metrics tool
2. Analyze the usage patterns for each mountpoint
3. Set appropriate thresholds considering:
    - Current usage
    - Historical trends
    - Safety margins (typically 10-15% below critical levels)
    - Specific characteristics of each mountpoint
4. Update the thresholds using update_thresholds tool. NOTE: If not applicable (no data available) for a mountpoint,
do not include it in the thresholds.

Respond with the final thresholds set for the instance.
"""


class ThresholdSetter:
    def __init__(self, prometheus: Prometheus, inventory_db: InventoryDB):
        self.prom = prometheus
        self.inventory_db = inventory_db
        self.agent_executor = create_react_agent(llm, self._create_tools(), prompt=THRESHOLD_ANALYSIS_PROMPT)

    def _create_tools(self) -> List[StructuredTool]:
        def get_disk_metrics(instance_id: str) -> Dict:
            """Fetch current and historical disk usage metrics for an instance"""
            current = self.prom.get_disk_usage(instance_id)
            historical = self.prom.get_disk_historical_usage(
                instance_id,
                datetime.now() - timedelta(days=30),
                datetime.now(),
                3600
            )
            return {"current_usage": current, "historical_data": historical}

        def update_thresholds(instance_id: str, thresholds: Thresholds) -> str:
            """Update instance thresholds in the database. Expects a Thresholds object."""
            self.inventory_db.update_thresholds(instance_id=instance_id, thresholds=thresholds)
            return f"Successfully updated thresholds for instance {instance_id}"

        return [
            StructuredTool.from_function(
                func=get_disk_metrics,
                name="get_disk_metrics",
                description="Fetch disk usage metrics for an instance. Returns current and historical usage data.",
            ),
            StructuredTool.from_function(
                func=update_thresholds,
                name="update_thresholds",
                description="Update instance thresholds in the database. Expects a Thresholds object."
            ),
        ]

    def run_thresholds_analysis(self, instance_id: str) -> None:
        """Run the threshold analysis for a given instance"""
        logger.info(f"Running thresholds analysis for instance {instance_id}")

        result = self.agent_executor.invoke({
            "messages": [
                {"role": "user", "content": f"Analyze and set thresholds for instance {instance_id}"}
            ]
        })

        logger.info(result['messages'][-1].content)


if __name__ == "__main__":
    prom = Prometheus(config.PROMETHEUS_ADDRESS)
    db_client = DatabaseClient({"uri": config.MONGO_DB_URI})
    inventory_db = InventoryDB(db_client.client)

    threshold_setter = ThresholdSetter(prom, inventory_db)

    logger.info("Starting threshold setter")
    for instance in inventory_db.get_instances():
        logger.info(f"Processing instance {instance.id}")
        threshold_setter.run_thresholds_analysis(instance_id=instance.id)
