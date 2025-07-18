import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection


class Status(Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLOSED = "closed"
    IGNORED = "ignored"


class Type(Enum):
    LOW_FREE_SPACE = "low_free_space"
    HIGH_CPU_USAGE = "high_cpu_usage"
    OTHER = "other"


class Incident(BaseModel):
    id: Optional[UUID] = None
    instance_id: Annotated[UUID, "ID of the instance"]
    status: Annotated[Status, "status of the incident"]
    type: Annotated[Type, "type of the incident"]
    data: Annotated[Any, "data related to the incident"] = None
    thread_id: Annotated[Optional[str], "ID of the thread"] = None
    created_at: Annotated[datetime, "time of creation"] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    response_endpoint: Annotated[Optional[str], "endpoint to send confirmation to"] = None


class IncidentDB:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client["incident_db"]
        self.incidents: Collection = self.db["incidents"]
        self.sysaidmin_db = mongo_client['sysaidmin']
        self.checkpoints: Collection = self.sysaidmin_db[
            'checkpoints'
        ]

    def get_incidents(
        self, status: Optional[Status] = None, type: Optional[Type] = None
    ) -> List[Incident]:
        query = {}
        if status:
            query["status"] = status.value
        if type:
            query["type"] = type.value
        return [Incident(**incident) for incident in self.incidents.find(query)]

    def get_incidents_by_instance_id(
        self,
        instance_id: UUID,
        status: Optional[Status] = None,
        type: Optional[Type] = None,
    ) -> List[Incident]:
        query = {"instance_id": str(instance_id)}
        if status:
            query["status"] = status.value
        if type:
            query["type"] = type.value
        return [Incident(**incident) for incident in self.incidents.find(query)]

    def create_incident(self, incident: Incident) -> Incident:
        incident.id = uuid4()
        self.incidents.insert_one(incident.model_dump(mode="json"))
        return incident

    def get_incident(self, incident_id: UUID) -> Incident:
        incident = self.incidents.find_one({"id": str(incident_id)})
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return Incident(**incident)

    def update_incident(self, incident: Incident) -> Incident:
        self.incidents.update_one(
            {"id": str(incident.id)}, {"$set": incident.model_dump(mode="json")}
        )
        return incident

    def update_status(self, incident_id: UUID, status: Status) -> Incident:
        incident = self.get_incident(incident_id)
        print(f"Updating incident {incident_id} to status {status}")
        if status == Status.CLOSED:
            traceback.print_stack()

        # Don't do anything if incident is already in target state
        if incident.status == status:
            return incident

        # Prevent invalid transitions (e.g., from CLOSED to another state)
        if incident.status in [Status.CLOSED, Status.IGNORED] and status not in [
            Status.CLOSED,
            Status.IGNORED,
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition incident from {incident.status.value} to {status.value}",
            )

        # Update if transition is valid
        incident.status = status
        return self.update_incident(incident)

    def get_incident_conversation(self, incident_id: UUID) -> List[dict]:
        checkpoints = list(
            self.checkpoints.find({"thread_id": str(incident_id)})
            .sort([("$natural", -1)])
            .limit(1)
        )
        if not checkpoints:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found for incident {incident_id}",
            )

        serde: SerializerProtocol = JsonPlusSerializer()
        checkpoint = serde.loads_typed(
            (checkpoints[0]["type"], checkpoints[0]["checkpoint"])
        )

        conversation = []
        for c in checkpoint.get("channel_values").get("messages"):
            # print(c)
            conversation.append(
                {"type": c.type, "name": c.name if c.name else "", "content": c.content}
            )

        return conversation


class Question(BaseModel):
    id: Optional[UUID] = None
    incident_id: UUID
    task_id: Optional[UUID] = None
    thread_ts: Optional[str] = None
    question_ts: Optional[str] = None
    question: str
    type: Literal["yesno", "ask"]
    response: Optional[str] = None


class QuestionDB:
    def __init__(self, mongo_client: MongoClient):
        self.db = mongo_client["question_db"]
        self.questions: Collection = self.db["questions"]

        try:
            self.questions.create_index(
                [("task_id", 1)],
                unique=True,
                partialFilterExpression={"task_id": {"$exists": True}},
            )
        except Exception as e:
            print(f"Note: Index may already exist: {e}")

    def create_question(self, question: Question) -> Question:
        question.id = uuid4()
        self.questions.insert_one(question.model_dump(mode="json"))
        return question

    def get_question(self, question_id: UUID) -> Question:
        question = self.questions.find_one({"id": str(question_id)})
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        return Question(**question)

    def delete_question(self, question_id: UUID):
        self.questions.delete_one({"id": str(question_id)})

    def update_question(self, question: Question) -> Question:
        self.questions.update_one(
            {"id": str(question.id)}, {"$set": question.model_dump(mode="json")}
        )
        return question
