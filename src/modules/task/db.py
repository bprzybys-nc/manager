from enum import Enum
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection


class Type(Enum):
    SHELL = "shell"
    PSQL = "psql"


class State(Enum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    HUMAN = "human"


class CommandType(Enum):
    DEBUG = "debug"
    FIX = "fix"


class Task(BaseModel):
    id: Optional[UUID] = None
    type: Annotated[Type, "type of the task"]
    batch_id: Annotated[UUID, "ID of the batch of tasks this task belongs to"]
    command: Annotated[str, "shell command to execute"]
    c_type: Annotated[CommandType, "type of the command"]
    reason: Annotated[str, "reason for issuing the command"]
    instance_id: Annotated[UUID, "ID of the instance"]
    incident_id: Annotated[UUID, "ID of the incident"]
    state: Annotated[Optional[State], "decision to approve or reject, or ask human"] = (
        None
    )
    comments: Annotated[List[str], "comments on the task"] = []
    output: Annotated[Optional[str], "output of the command"] = None
    question: Annotated[Optional[UUID], "ID of a question if valid"] = None
    created_at: Annotated[datetime, "time of creation"] = Field(default_factory=lambda: datetime.now(timezone.utc))
    cmdb_metadata: Annotated[Optional[dict], "metadata of the CMDB"] = None


class BatchTasks(BaseModel):
    id: UUID
    incident_id: UUID
    task_ids: List[UUID]
    visible: bool = True


class TaskDB:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client["task_db"]
        self.tasks: Collection = self.db["tasks"]
        self.batch_tasks: Collection = self.db["batch_tasks"]

    def get_task(self, task_id: UUID) -> Task:
        return Task(**self.tasks.find_one({"id": str(task_id)}))

    def get_tasks_by_incident_id(
        self, incident_id: UUID, state: Optional[State] = None
    ) -> List[Task]:
        query = {"incident_id": str(incident_id)}
        if state:
            query["state"] = state.value
        return [Task(**task) for task in self.tasks.find(query)]

    def create_task(self, task: Task) -> Task:
        if not task.id:
            task.id = uuid4()
        print(f"Creating task: {task}")
        self.tasks.insert_one(task.model_dump(mode="json"))
        return task

    def add_output(self, task_id: UUID, output: str):
        self.tasks.update_one(
            {"id": str(task_id)},
            {"$set": {"output": output, "state": State.COMPLETED.value}},
        )

    def update_state(self, task_id: UUID, state: State):
        self.tasks.update_one({"id": str(task_id)}, {"$set": {"state": state.value}})

    def get_tasks_by_batch_id(self, batch_id: UUID) -> List[Task]:
        return [Task(**task) for task in self.tasks.find({"batch_id": str(batch_id)})]

    def create_batch_tasks(
        self, incident_id: UUID, batch_id: UUID, task_ids: List[UUID]
    ) -> UUID:
        self.batch_tasks.insert_one(
            BatchTasks(
                id=batch_id, incident_id=incident_id, task_ids=task_ids
            ).model_dump(mode="json")
        )
        return batch_id

    def get_visible_batch_tasks(self, incident_id: UUID) -> BatchTasks:
        bt = self.batch_tasks.find_one(
            {"incident_id": str(incident_id), "visible": True}
        )
        if not bt:
            return None
        return BatchTasks(**bt)

    def hide_batch_tasks(self, incident_id: UUID, batch_id: UUID) -> None:
        self.batch_tasks.update_many(
            {"incident_id": str(incident_id), "id": str(batch_id)},
            {"$set": {"visible": False}},
        )

    def add_comment(self, task_id: UUID, comment: str) -> Task:
        task = self.get_task(task_id)
        task.comments.append(comment)
        self.tasks.update_one(
            {"id": str(task_id)}, {"$set": task.model_dump(mode="json")}
        )
        return task
