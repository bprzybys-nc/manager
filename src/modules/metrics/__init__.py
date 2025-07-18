from fastapi import APIRouter, HTTPException, Request, Response

from .prometheus import Prometheus
from .storage import Storage
from src.modules.inventory.db import InventoryDB


class MetricsRoute:
    def __init__(self, storage: Storage, prometheus: Prometheus, inventory_db: InventoryDB):
        self.router = APIRouter()
        self.storage = storage
        self.prometheus = prometheus
        self.inventory_db = inventory_db
        self._setup_routes()

    def _setup_routes(self):
        self.router.get("/instances")(self.get_scrape_targets)
        self.router.post("/instances/{instance_id}")(self.store_metrics)
        self.router.get("/instances/{instance_id}")(self.get_metrics)
        self.router.get("/instances/{instance_id}/free_space")(self.get_free_space)

    async def get_scrape_targets(self):
        return self.prometheus.get_scrape_targets(self.inventory_db.get_instances())

    async def store_metrics(self, request: Request, instance_id: str):
        metrics_data = await request.body()
        self.storage.store(instance_id, metrics_data.decode('utf-8'))
        self.inventory_db.update_last_ping(instance_id)
        return {"message": "Metrics received successfully"}

    async def get_metrics(self, instance_id: str):
        content = self.storage.retrieve(instance_id)
        if content is None:
            raise HTTPException(status_code=404, detail="Metrics not found")

        return Response(
            content=content,
            media_type="text/plain; version=0.0.4; charset=utf-8; escaping=values"
        )

    async def get_free_space(self, instance_id: str):
        free_space = self.prometheus.get_free_space(instance_id)
        return free_space
