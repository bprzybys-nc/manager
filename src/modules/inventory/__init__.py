from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter

from .db import Instance, InstanceRegister, InventoryDB, Metadata, Process


class InventoryRoute:
    def __init__(self, db: InventoryDB):
        self.router = APIRouter()
        self.db = db
        self._setup_routes()

    def _setup_routes(self):
        self.router.post("/register")(self.register_instance)
        self.router.get("/instances", response_model=List[Instance])(self.get_instances)
        self.router.get("/instances/{instance_id}", response_model=Instance)(self.get_instance)
        self.router.post("/instances/{instance_id}/ping")(self.update_last_ping)
        self.router.post("/instances/{instance_id}/metadata")(self.update_metadata)
        self.router.post("/instances/{instance_id}/processes")(self.update_processes)

    async def get_instances(self, status: Optional[str] = None):
        """Get list of instances, optionally filtered by status"""
        return self.db.get_instances(status)

    async def get_instance(self, instance_id: UUID):
        """Get configuration for a specific instance"""
        return self.db.get_instance(instance_id)

    async def register_instance(self, instance: InstanceRegister):
        """Register a new instance with its configuration"""
        self.db.register_instance(instance.id, instance.metadata)
        return {"message": "Instance registered successfully"}

    async def update_last_ping(self, instance_id: UUID):
        """Update last ping time for an instance"""
        self.db.update_last_ping(instance_id)
        return {"message": "Last ping updated successfully"}

    async def update_metadata(self, instance_id: UUID, metadata: Metadata):
        """Update metadata for an instance"""
        self.db.update_metadata(instance_id, metadata)
        return {"message": "Metadata updated successfully"}

    async def update_processes(self, instance_id: UUID, processes: List[Process]):
        """Update processes for an instance"""
        self.db.update_processes(instance_id, processes)
        return {"message": "Processes updated successfully"}