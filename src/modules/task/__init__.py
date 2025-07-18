from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from src.modules.cmdb.metadata import CMDBMetadata
from src.modules.incident.db import IncidentDB
from .db import State, Task, TaskDB, Type


class TaskResult(BaseModel):
    output: str


class TaskRoute:
    def __init__(self, db: TaskDB, idb: IncidentDB, cmdb_metadata: CMDBMetadata):
        self.router = APIRouter()
        self.db = db
        self.idb = idb
        self.cmdb_metadata = cmdb_metadata
        self._setup_routes()

    def _setup_routes(self):
        self.router.get("/incidents/{incident_id}")(self.get_tasks)

        self.router.post("/{task_id}/ack")(self.ack_task)
        self.router.post("/{task_id}/result")(self.save_result)
        self.router.put("/{task_id}/state/{state}")(self.update_state)

        self.router.get("/batch/incidents/{incident_id}")(self.get_batch_tasks)

    async def get_tasks(self, incident_id: str, state: State) -> List[Task]:
        return self.db.get_tasks_by_incident_id(incident_id, state)

    async def ack_task(self, task_id: str) -> None:
        self.db.update_state(task_id, State.IN_PROGRESS)

    async def save_result(self, task_id: str, result: TaskResult) -> None:
        self.db.add_output(task_id, result.output)

    async def update_state(self, task_id: str, state: State) -> Task:
        task = self.db.get_task(task_id)
        task.state = state
        self.db.update_state(task_id, state)
        return task

    async def get_batch_tasks(self, incident_id: str) -> List[Task]:
        bt = self.db.get_visible_batch_tasks(incident_id)
        if not bt:
            return []
        self.db.hide_batch_tasks(bt.incident_id, bt.id)
        tasks = [self.db.get_task(task_id) for task_id in bt.task_ids]

        incident = self.idb.get_incident(incident_id)

        for task in tasks:
            if task.type == Type.PSQL:
                task.cmdb_metadata = self.cmdb_metadata.get_metadata(incident.instance_id)

        return tasks
