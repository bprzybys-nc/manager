from enum import Enum
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection


class ThresholdDiskPartition(BaseModel):
    mountpoint: Annotated[str, "mount point of the partition"]
    usage: Annotated[float, "threshold for disk usage"]


class Thresholds(BaseModel):
    disk_partitions: Annotated[Optional[List[ThresholdDiskPartition]], "thresholds for disk partitions"]


class Config(BaseModel):
    thresholds: Annotated[Optional[Thresholds], "thresholds for metrics"]


class HostInfo(BaseModel):
    hostname: Annotated[str, "hostname of the system"]
    os: Annotated[str, "operating system name"]
    platform: Annotated[str, "platform identifier"]
    platform_family: Annotated[str, "platform family"]
    platform_version: Annotated[str, "platform version"]
    kernel_version: Annotated[str, "kernel version"]


class VirtualMemory(BaseModel):
    total: Annotated[int, "total virtual memory in bytes"]
    free: Annotated[int, "free virtual memory in bytes"]


class DiskPartition(BaseModel):
    mountpoint: Annotated[str, "mount point of the partition"]
    device: Annotated[str, "device path"]
    fstype: Annotated[str, "filesystem type"]
    total: Annotated[int, "total size in bytes"]


class Process(BaseModel):
    pid: Annotated[int, "process ID"]
    name: Annotated[Optional[str], "process name"]
    status: Annotated[Optional[list[str]], "status of the process"]
    username: Annotated[Optional[str], "username of the process owner"]
    cmd: Annotated[Optional[str], "command used to start the process"]
    cpu_percent: Annotated[Optional[float], "CPU percentage used by the process"]
    memory_percent: Annotated[Optional[float], "memory percentage used by the process"]


class Metadata(BaseModel):
    host_info: Annotated[Optional[HostInfo], "system information about the host"]
    virtual_memory: Annotated[Optional[VirtualMemory], "virtual memory information"]
    disk_partitions: Annotated[Optional[List[DiskPartition]], "list of disk partitions"]


class InstanceStatus(Enum):
    ACTIVE = "active"
    OFFLINE = "offline"


class Instance(BaseModel):
    id: UUID
    metadata: Annotated[Optional[Metadata], "metadata of the instance"] = None
    processes: Annotated[Optional[List[Process]], "list of processes running on the instance"] = None
    config: Annotated[Optional[Config], "configuration of the instance"] = None
    last_ping: Annotated[datetime, "last ping time"] = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Annotated[InstanceStatus, "status of the instance"] = InstanceStatus.ACTIVE
    created_at: Annotated[datetime, "time of creation"] = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        if self.last_ping:
            last_ping = self.last_ping.replace(tzinfo=timezone.utc) if self.last_ping.tzinfo is None else self.last_ping
            if (datetime.now(timezone.utc) - last_ping).total_seconds() > 60:
                self.status = InstanceStatus.OFFLINE
            else:
                self.status = InstanceStatus.ACTIVE


class InstanceRegister(BaseModel):
    id: UUID
    metadata: Annotated[Optional[Metadata], "metadata of the instance"] = None


class InventoryDB:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client["inventory_db"]
        self.instances: Collection = self.db["instances"]

    def register_instance(self, instance_id: UUID, metadata: Metadata) -> None:
        instance = Instance(id=instance_id, metadata=metadata)
        self.instances.insert_one(instance.model_dump(mode="json"))

    def update_last_ping(self, instance_id: UUID) -> None:
        result = self.instances.update_one(
            {"id": str(instance_id)},
            {"$set": {"last_ping": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Instance not found")

    def update_metadata(self, instance_id: UUID, metadata: Metadata) -> None:
        result = self.instances.update_one(
            {"id": str(instance_id)},
            {"$set": {"metadata": metadata.model_dump(mode="json")}},
            upsert=True
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Instance not found")

    def update_thresholds(self, instance_id: UUID, thresholds: Thresholds) -> None:
        result = self.instances.update_one(
            {"id": str(instance_id)},
            {
                "$set": {
                    "config": {"thresholds": thresholds.model_dump(mode="json")}
                }
            },
            upsert=True
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Instance not found")

    def get_instances(self, status: Optional[str] = None) -> List[Instance]:
        query = {"status": status} if status else {}
        return [Instance(**instance) for instance in self.instances.find(query)]

    def get_instance(self, instance_id: UUID) -> Instance:
        instance = self.instances.find_one({"id": str(instance_id)})
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        return Instance(**instance)

    def update_processes(self, instance_id: UUID, processes: List[Process]) -> None:
        result = self.instances.update_one(
            {"id": str(instance_id)},
            {"$set": {"processes": [process.model_dump(mode="json") for process in processes]}},
            upsert=True
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Instance not found")
