import logging
from typing import Any, Dict, List

import requests
from celery import Celery
from fastapi import APIRouter
from pydantic import BaseModel

from src.modules.task.db import State, TaskDB
from .db import Incident, IncidentDB, QuestionDB, Status, Type


class IncidentTaskDone(BaseModel):
    task_ids: List[str]


class BatchCompletionRequest(BaseModel):
    batch_id: str
    task_results: List[Dict[str, Any]]


class IncidentRoute:
    def __init__(
        self,
        db: IncidentDB,
        qdb: QuestionDB,
        tdb: TaskDB,
        task_broker: Celery,
    ):
        self.router = APIRouter()
        self.db = db
        self.qdb = qdb
        self.tdb = tdb
        self.task_broker = task_broker
        self._setup_routes()

    def _setup_routes(self):
        self.router.get("/instances/{instance_id}")(self.get_incidents)
        self.router.get("/")(self.get_all_incidents)
        self.router.get("/{incident_id}")(self.get_incident)
        self.router.get("/{incident_id}/conversation")(self.get_incident_conversation)
        self.router.post("/{incident_id}/ack")(self.ack_incident)
        self.router.put("/{incident_id}/status/{status}")(self.update_status)
        self.router.post("/{incident_id}/tasks-done")(self.tasks_done)
        # Fix the path to match what the Go agent is sending
        self.router.post("/tasks/batch/completed")(
            self.batch_completed
        )  # Keep for backward compatibility
        self.router.post("/incidents/tasks/batch/completed")(
            self.batch_completed
        )  # Add new route for agent

    async def get_incidents(
        self, instance_id: str, status: Status = None, type: Type = None
    ) -> List[Incident]:
        print(
            "get_incidents", "instance_id", instance_id, "status", status, "type", type
        )
        return self.db.get_incidents_by_instance_id(instance_id, status, type)

    async def get_all_incidents(
        self, status: Status = None, type: Type = None
    ) -> List[Incident]:
        return self.db.get_incidents(status, type)

    async def get_incident(self, incident_id: str) -> Incident:
        return self.db.get_incident(incident_id)

    async def get_incident_conversation(self, incident_id: str) -> List[dict]:
        return self.db.get_incident_conversation(incident_id)

    async def ack_incident(self, incident_id: str) -> Incident:
        incident = self.db.get_incident(incident_id)
        incident.status = Status.ACKNOWLEDGED
        self.db.update_incident(incident)

        if incident.type != Type.OTHER:
            self.task_broker.send_task("run_incident_assistant", (incident.id, [], []))

        return incident

    async def update_status(self, incident_id: str, status: Status) -> Incident:
        incident = self.db.get_incident(incident_id)
        incident.status = status
        self.db.update_incident(incident)
        return incident

    async def tasks_done(self, incident_id: str, tasks_done: IncidentTaskDone):
        incident = self.db.get_incident(incident_id)

        if incident.type == Type.OTHER:
            try:
                requests.post(
                    incident.response_endpoint,
                    json={
                        "incident_id": str(incident.id),
                        "tasks_done": tasks_done.task_ids,
                    }
                )
            except requests.RequestException as e:
                logging.error(
                    f"Error sending tasks done notification to {incident.response_endpoint}: {e}"
                )
        else:
            self.task_broker.send_task(
                "run_incident_assistant", (incident.id, tasks_done.task_ids, [])
            )

    async def batch_completed(self, request: BatchCompletionRequest):
        """Handle notification that a batch of tasks has been completed by the agent"""
        logging.info(f"Received completion notification for batch: {request.batch_id}")

        try:
            # Log detailed information about received results
            task_count = len(request.task_results) if request.task_results else 0
            logging.info(f"Batch {request.batch_id} contains {task_count} task results")

            # Debug each result
            for i, result in enumerate(request.task_results):
                task_id = result.get("task_id", "unknown")
                cmd = result.get("command", "unknown")
                output_size = len(result.get("output", ""))
                logging.info(
                    f"Task {i+1}/{task_count}: ID={task_id}, cmd='{cmd}', output size={output_size} bytes"
                )

            # IMPROVED: Make more robust workflow retrieval - try multiple collections
            workflow_info = None

            # First try nil_process collection
            workflow_info = self.tdb.db.client["workflow_status"][
                "nil_process"
            ].find_one({"batch_id": request.batch_id})

            # If not found, try string conversion
            if not workflow_info:
                logging.info(
                    f"Trying alternative batch ID format for {request.batch_id}"
                )
                workflow_info = self.tdb.db.client["workflow_status"][
                    "nil_process"
                ].find_one({"batch_id": str(request.batch_id)})

            # If still not found, try pending_tasks as fallback
            if not workflow_info:
                logging.info("Trying pending_tasks collection as fallback")
                workflow_info = self.tdb.db.client["workflow_status"][
                    "pending_tasks"
                ].find_one({"batch_id": request.batch_id})

            # If still nothing, try by task IDs
            if (
                not workflow_info
                and request.task_results
                and len(request.task_results) > 0
            ):
                task_id = request.task_results[0].get("task_id")
                if task_id:
                    logging.info(f"Trying to find batch by task ID: {task_id}")
                    task = self.tdb.get_task(task_id)
                    if task and task.batch_id:
                        batch_id_str = str(task.batch_id)
                        workflow_info = self.tdb.db.client["workflow_status"][
                            "nil_process"
                        ].find_one({"batch_id": batch_id_str})
                        if workflow_info:
                            logging.info(
                                f"Found workflow via task's batch_id: {batch_id_str}"
                            )

            if not workflow_info:
                logging.warning(
                    f"No pending workflow found for batch: {request.batch_id}"
                )
                # Process anyway since we have task results
                if request.task_results and len(request.task_results) > 0:
                    # Try to find the incident ID from the tasks
                    first_task_id = request.task_results[0].get("task_id")
                    if first_task_id:
                        task = self.tdb.get_task(first_task_id)
                        if task and task.incident_id:
                            # Create a workflow_info with what we know
                            workflow_info = {"incident_id": str(task.incident_id)}
                            logging.info(
                                f"Created workflow info from task: {workflow_info}"
                            )

            if not workflow_info:
                return {"status": "no_workflow_found"}

            logging.info(
                f"Found workflow: incident_id={workflow_info.get('incident_id')}"
            )

            # Extract task IDs from results
            task_ids = []

            # Update tasks with output if provided
            for result in request.task_results:
                if not result.get("task_id"):
                    logging.warning(f"Missing task_id in result: {result}")
                    continue

                task_ids.append(result["task_id"])

                try:
                    task = self.tdb.get_task(result["task_id"])
                    if not task:
                        logging.warning(f"Task not found: {result['task_id']}")
                        continue

                    # Handle output processing
                    if "output" in result:
                        # Ensure output isn't too large for MongoDB (16MB limit)
                        output = result["output"]
                        if len(output) > 15 * 1024 * 1024:  # 15MB safety limit
                            logging.warning(
                                f"Output too large ({len(output)} bytes) for task {result['task_id']}, truncating"
                            )
                            output = (
                                output[: 15 * 1024 * 1024]
                                + "\n... [OUTPUT TRUNCATED DUE TO SIZE LIMITS] ..."
                            )

                        # Update output and state separately using existing methods
                        self.tdb.add_output(result["task_id"], output)
                        logging.info(
                            f"Updated task {result['task_id']} with {len(output)} bytes of output"
                        )
                    else:
                        logging.warning(
                            f"No output provided for task {result['task_id']}"
                        )
                        self.tdb.update_state(result["task_id"], State.COMPLETED)
                except Exception as e:
                    logging.error(
                        f"Error updating task {result['task_id']}: {str(e)}",
                        exc_info=True,
                    )

            # Update workflow status
            try:
                # Use batch_id for querying instead of _id
                if workflow_info.get("_id"):
                    self.tdb.db.client["workflow_status"]["pending_tasks"].update_one(
                        {"_id": workflow_info["_id"]}, {"$set": {"status": "completed"}}
                    )
                else:
                    # Update using batch_id instead
                    self.tdb.db.client["workflow_status"]["pending_tasks"].update_one(
                        {"batch_id": request.batch_id},
                        {"$set": {"status": "completed"}},
                    )
                logging.info(
                    f"Updated workflow status to 'completed' for batch {request.batch_id}"
                )
            except Exception as e:
                logging.error(
                    f"Error updating workflow status: {str(e)}", exc_info=True
                )

            # Resume the workflow
            try:
                incident_id = workflow_info["incident_id"]
                incident = self.db.get_incident(incident_id)

                if not incident:
                    logging.error(f"Could not find incident {incident_id}")
                    return {
                        "status": "error",
                        "message": f"Incident {incident_id} not found",
                    }

                logging.info(
                    f"Resuming workflow for incident: {incident_id}, tasks: {task_ids}"
                )

                # IMPORTANT CHANGE: Set explicit incident context in the first message
                # This ensures all agents know which incident they're working on
                context_message = (
                    f"## Task Execution Results for Incident: {incident_id}\n"
                    f"- **Incident ID**: {incident_id}\n"
                    f"- **Tasks Batch ID**: {request.batch_id}\n\n"
                    f"The following tasks have been executed. Review the results and determine next steps:\n\n"
                )

                # Send a task with explicit incident ID emphasis to the incident broker
                if incident.type != Type.OTHER:
                    self.task_broker.send_task(
                        "run_incident_assistant", (incident.id, task_ids, [])
                    )

                return {"status": "success"}

            except Exception as e:
                logging.error(f"Error resuming workflow: {str(e)}", exc_info=True)
                return {"status": "error", "message": str(e)}

        except Exception as e:
            logging.error(
                f"Unexpected error in batch_completed: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": str(e)}
