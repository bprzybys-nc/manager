import os
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, List, Literal, Optional
from uuid import UUID, uuid4
import re

import openai
import src.config as config
from langchain.tools import StructuredTool
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool, tool
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import Messages
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from src.database.client import DatabaseClient
from src.integrations.hil.hil import HILIntegration
from src.llm import llm
from src.modules.inventory.db import InventoryDB
from src.modules.task.db import State, Task, TaskDB
from src.modules.incident.agent_prompts import AgentPrompts

from .db import Incident, IncidentDB, Question, QuestionDB, Status

# Create a global TaskDB instance for tools
dbc = DatabaseClient({"uri": config.MONGO_DB_URI})
task_db = TaskDB(dbc.client)
incident_db = IncidentDB(dbc.client)
question_db = QuestionDB(dbc.client)

lf_handler = CallbackHandler()


@dataclass
class AgentConfig:
    name: str
    prompt: str
    tools: List | None = None


class DBTools:
    def __init__(self, incident_db: IncidentDB, task_db: TaskDB):
        self.incident_db = incident_db
        self.task_db = task_db
        self.incident_assistant = None

        self.create_task = StructuredTool.from_function(
            func=self._create_task,
            name="create_task",
            description="Create a task in the TaskDB.",
        )
        self.list_tasks = StructuredTool.from_function(
            func=self._list_tasks,
            name="list_tasks",
            description="List all pending approval tasks.",
        )
        self.change_task = StructuredTool.from_function(
            func=self._change_task,
            name="change_task",
            description="Approve, reject or send for human approval a task.",
        )
        self.close_incident = StructuredTool.from_function(
            func=self._close_incident,
            name="close_incident",
            description="Close an incident.",
        )

    def _create_task(self, task: Annotated[Task, "Task object to create"]) -> Task:
        """Create a task in the TaskDB."""
        if not task.state:
            task.state = State.CREATED
        # Check if a task with the same command already exists for this incident
        if hasattr(task, 'incident_id') and hasattr(task, 'command'):
            existing_tasks = self.task_db.get_tasks_by_incident_id(task.incident_id)
            for existing_task in existing_tasks:
                if existing_task.command == task.command and existing_task.batch_id == task.batch_id:
                    print(f"Duplicate task detected: {task.command}")
                    return "This command was already proposed!"  # Return the existing task instead of creating a duplicate
        return self.task_db.create_task(task)

    def _list_tasks(self, incident_id: str):
        """List all pending approval tasks."""
        return self.task_db.get_tasks_by_incident_id(incident_id, state=State.CREATED)

    def _change_task(
        self,
        id: Annotated[str, "task id (uuid)"],
        state: Annotated[
            State, "approval decision as State (approved, rejected, human)"
        ],
        comment: Annotated[Optional[str], "comment to add to the task"] = None,
    ):
        """Approve or reject a task. Use state HUMAN for asking for a human approval"""
        if comment:
            self.task_db.add_comment(id, comment)
        return self.task_db.update_state(id, state)

    def _close_incident(self, incident_id: str, reason: str = "Issue resolved"):
        """Close an incident after verifying no pending tasks remain."""
        try:
            # 1. Check for pending tasks
            pending_tasks = self.task_db.get_tasks_by_incident_id(
                incident_id, state=State.CREATED
            )
            executing_tasks = self.task_db.get_tasks_by_incident_id(
                incident_id, state=State.IN_PROGRESS
            )

            # 2. Also check for any tasks in batch that haven't been executed
            workflow_status = self.task_db.db.client["workflow_status"][
                "nil_process"
            ].find_one({"incident_id": str(incident_id), "execution_complete": False})

            # 3. Block closure if pending tasks or batches exist
            if pending_tasks:
                return (
                    f"Error: Cannot close incident {incident_id} - {len(pending_tasks)} tasks still await review. "
                    f"All tasks must be approved, rejected, or deleted before closure."
                )

            if executing_tasks:
                return (
                    f"Error: Cannot close incident {incident_id} - {len(executing_tasks)} tasks are still executing. "
                    f"All tasks must complete execution before closure."
                )

            if workflow_status:
                return (
                    f"Error: Cannot close incident {incident_id} - batch {workflow_status.get('batch_id')} "
                    f"is still pending execution. Wait for execution to complete."
                )

            # 4. Verify the incident exists before attempting to close it
            incident = self.incident_db.get_incident(incident_id)
            if not incident:
                return f"Error: Incident {incident_id} not found"

            # 5. All checks passed - close the incident
            result = self.incident_db.update_status(incident_id, Status.CLOSED)


            print(f"Successfully closed incident {incident_id} with reason: {reason}")
            return f"Incident {incident_id} closed successfully: {reason}"
        except Exception as e:
            error_msg = f"Error closing incident {incident_id}: {str(e)}"
            print(error_msg)
            return error_msg

    def _validate_closure_requirements(self, incident_id: str, reason: str) -> bool:
        """Validate that incident meets requirements for closure"""
        # Get all tasks for this incident
        tasks = self.task_db.get_tasks_by_incident_id(incident_id)
        incident = self.incident_db.get_incident(incident_id)

        # Must have executed at least 2 diagnostic commands
        if len(tasks) < 2:
            print(f"Rejecting incident closure: insufficient diagnostics ({len(tasks)} tasks)")
            return False

        # For CPU issues, require evidence of normal CPU levels
        if incident.type == Type.HIGH_CPU_USAGE:
            # Look for CPU measurements in task outputs
            cpu_verified = False
            for task in tasks:
                if task.state == State.COMPLETED and task.output:
                    if "CPU usage:" in task.output and "idle" in task.output:
                        # Extract idle percentage
                        match = re.search(r"(\d+\.\d+)% idle", task.output)
                        if match and float(match.group(1)) > 70:
                            cpu_verified = True
                            break

            if not cpu_verified:
                print("Rejecting incident closure: CPU usage not verified to be normal")
                return False

        # Similar checks for disk space issues

        # Check if SysAdmin claims to have killed processes but hasn't verified
        kill_commands_executed = False
        kill_verification_found = False

        for task in tasks:
            # Look for kill commands
            if task.state in [State.COMPLETED, State.APPROVED] and task.command:
                if any(cmd in task.command.lower() for cmd in ["kill", "pkill", "killall"]):
                    kill_commands_executed = True
                    # Now look for verification after kill commands
                    for verify_task in tasks:
                        if verify_task.id != task.id and verify_task.created_at > task.created_at:
                            if any(cmd in verify_task.command.lower() for cmd in ["ps", "top", "pgrep"]):
                                kill_verification_found = True
                                break

        if kill_commands_executed and not kill_verification_found:
            print("Rejecting incident closure: Kill command executed without verification")
            return False

        print(f"Incident closure validated: {reason}")
        return True


class IncidentAssistant:
    def __init__(
        self,
        db_client: DatabaseClient,
        hil_integration: Optional[HILIntegration] = None,
        recursion_limit: int = 35,
    ):
        self.incident = None
        self.instance = None
        self.tasks_batch_id = None
        self.db = db_client
        self._setup_databases(db_client)
        self._setup_tools()
        self._setup_agents()
        self.network = self._create_network()
        self.hil_integration = hil_integration
        self.recursion_limit = recursion_limit

    def _setup_databases(self, db_client: DatabaseClient) -> None:
        self.incident_db = IncidentDB(db_client)
        self.inventory_db = InventoryDB(db_client)
        self.task_db = TaskDB(db_client)
        self.checkpointer = MongoDBSaver(
            client=db_client,
            db_name="sysaidmin",
            writes_collection_name="workflow_checkpoints",
        )

    def _setup_tools(self) -> None:
        self.db_tools = DBTools(self.incident_db, self.task_db)
        self.db_tools.incident_assistant = self

    def _setup_agents(self) -> None:
        agent_prompts = AgentPrompts()

        self.agents = {
            "incident": self._create_agent(
                AgentConfig(
                    "incident",
                    agent_prompts.INCIDENT_ASSISTANT,
                    [StructuredTool.from_function(self.update_status)],
                )
            ),
            "sysadmin": self._create_agent(
                AgentConfig(
                    "sysadmin",
                    agent_prompts.SYSADMIN,
                    [
                        self.db_tools.create_task,
                        self.db_tools.close_incident
                    ],
                )
            ),
            "ciso": self._create_agent(
                AgentConfig(
                    "ciso",
                    agent_prompts.CISO,
                    [
                        self.db_tools.list_tasks,
                        self.db_tools.change_task,
                    ],
                )
            ),
        }

    def _create_agent(self, config: AgentConfig):
        return create_react_agent(
            llm,
            config.tools or [],
            prompt=config.prompt,
            checkpointer=self.checkpointer,
            debug=False,
        )

    def _create_network(self):
        builder = StateGraph(MessagesState)

        # Add nodes
        builder.add_node("incident_agent", self.agents["incident"])
        builder.add_node("sysadmin_agent", self.sysadmin_node)
        builder.add_node("ciso_agent", self.ciso_node)

        # Replace nil with two nodes
        builder.add_node("nil_prepare", self.nil_prepare_node)
        builder.add_node("nil_wait", self.nil_wait_node)

        # HIL flow nodes
        builder.add_node("hil_prepare", self.hil_prepare_node)
        builder.add_node("hil_wait", self.hil_wait_node)

        # Add edges
        builder.add_edge("nil_wait", "incident_agent")
        builder.add_edge("nil_prepare", "nil_wait")  # Important: prepare -> wait
        builder.add_edge("hil_wait", "incident_agent")
        builder.add_edge("hil_prepare", "hil_wait")
        builder.add_edge(START, "incident_agent")
        builder.add_conditional_edges("incident_agent", self.route_next_agent)

        return builder.compile(checkpointer=self.checkpointer)

    def route_next_agent(
        self, state: MessagesState
    ) -> Literal["ciso_agent", "sysadmin_agent", "nil_prepare", "hil_prepare", END]:
        # Update return type to include new node names

        if self.incident_db.get_incident(self.incident.id).status in [
            Status.CLOSED,
            Status.IGNORED,
        ]:
            return END

        tasks = self.task_db.get_tasks_by_batch_id(self.tasks_batch_id)
        if not tasks:
            return "sysadmin_agent"
        if len([t for t in tasks if t.state == State.CREATED]) > 0:
            return "ciso_agent"

        # Check if we have human tasks
        human_tasks = list([t for t in tasks if t.state == State.HUMAN])
        if len(human_tasks) > 0:
            print(f"Found {len(human_tasks)} tasks requiring human approval")
            return "hil_prepare"

        return "nil_prepare"

    def sysadmin_node(self, state: MessagesState) -> Command[Literal["incident_agent"]]:
        # Add context preservation
        state_with_context = self._preserve_incident_context(state)

        result = self.agents["sysadmin"].invoke(
            state_with_context, config={"recursion_limit": self.recursion_limit, "configurable": {"thread_id": str(self.incident.id)}}
        )

        #Check if incident is closed before proceeding
        current_incident = self.incident_db.get_incident(self.incident.id)

        if current_incident.status in [Status.CLOSED, Status.IGNORED]:
            print(f"Incident {self.incident.id} is closed or ignored. Exiting the workflow.")
            return Command(
                update={
                    "messages": [
                        AIMessage(
                            content=f"Incident ID: {self.incident.id} is already {current_incident.status.value}. No further action needed.",
                            name="sysadmin_agent"
                        )
                    ]
                },
                goto="END"
            )
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=f"Incident ID: {self.incident.id}\n{result['messages'][-1].content}",
                        name="sysadmin_agent"
                    )
                ]
            },
            goto="incident_agent",
        )

    def ciso_node(self, state: MessagesState) -> Command[Literal["incident_agent"]]:
        # Add context preservation
        state_with_context = self._preserve_incident_context(state)

        result = self.agents["ciso"].invoke(
            state_with_context, config={"recursion_limit": self.recursion_limit, "configurable": {"thread_id": str(self.incident.id)}}
        )
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=f"Incident ID: {self.incident.id}\n{result['messages'][-1].content}",
                        name="ciso_agent"
                    )
                ]
            },
            goto="incident_agent",
        )

    def nil_prepare_node(self, state: Messages):
        """Prepares tasks for execution but doesn't interrupt"""
        workflow_status = self.db.client["workflow_status"]["hil_process"].find_one({
            "batch_id": str(self.tasks_batch_id),
            "waiting": True  # This indicates we're already waiting for responses
        })

        if workflow_status:
            print(f"Batch {self.tasks_batch_id} already waiting for human responses, skipping duplicate question creation")
            # Skip directly to wait node since questions already exist
            return Command(goto="hil_wait")
        tasks = self.task_db.get_tasks_by_batch_id(self.tasks_batch_id)

        # If there are still tasks in human approval, route to HIL prepare node
        if tasks and any(map(lambda t: t.state == State.HUMAN, tasks)):
            return Command(goto="hil_prepare")

        # For tasks ready for execution, check if they've already been batched
        if tasks and all(t.state in [State.APPROVED, State.REJECTED] for t in tasks):
            # Check workflow status to see if we've processed this batch already
            workflow_status = self.db.client["workflow_status"]["nil_process"].find_one({
                "batch_id": str(self.tasks_batch_id)
            })

            # If we've already executed this batch, skip to incident agent
            if workflow_status and workflow_status.get("execution_complete", False):
                print(f"Batch {self.tasks_batch_id} already executed ({workflow_status.get('completed_at')})")
                return Command(goto="incident_agent")

            # If we haven't created the batch yet, do it now
            if not workflow_status or not workflow_status.get("batch_created"):
                print(f"Creating new batch tasks for batch {self.tasks_batch_id}")

                # First time through - create batch tasks
                self.task_db.create_batch_tasks(
                    self.incident.id,
                    self.tasks_batch_id,
                    [t.id for t in tasks if t.state == State.APPROVED],
                )

                # Mark that we've created the batch
                self.db.client["workflow_status"]["nil_process"].update_one(
                    {"batch_id": str(self.tasks_batch_id)},
                    {"$set": {
                        "incident_id": str(self.incident.id),
                        "batch_created": True,
                        "created_at": datetime.now()
                    }},
                    upsert=True
                )

            # Now continue to nil_wait node for execution
            return Command(goto="nil_wait")

        # No approved/rejected tasks - just continue workflow
        return Command(goto="incident_agent")

    def nil_wait_node(self, state: Messages):
        """Handles the interrupt/wait for task execution"""
        print(f"Interrupting for execution of batch {self.tasks_batch_id}")

        # Fetch tasks that need to be executed
        tasks = self.task_db.get_tasks_by_batch_id(self.tasks_batch_id)

        # Create interrupt value with explicit incident context
        value = interrupt({
            "tasks": tasks,
            "incident_id": str(self.incident.id),
            "incident_context": f"Incident ID: {self.incident.id}"
        })

        # After resumption, mark that execution is complete
        # This only happens once after the interrupt is resolved
        print(f"Resuming after execution of batch {self.tasks_batch_id}")
        self.db.client["workflow_status"]["nil_process"].update_one(
            {"batch_id": str(self.tasks_batch_id)},
            {"$set": {"execution_complete": True, "completed_at": datetime.now()}}
        )

        # Continue workflow
        return Command(goto="incident_agent")

    def hil_prepare_node(self, state: Messages):
        """Prepares questions for human approval but doesn't interrupt"""
        workflow_status = self.db.client["workflow_status"]["hil_process"].find_one({
            "batch_id": str(self.tasks_batch_id),
            "waiting": True  # This indicates we're already waiting for responses
        })

        if workflow_status:
            print(f"Batch {self.tasks_batch_id} already waiting for human responses, skipping duplicate question creation")
            # Skip directly to wait node since questions already exist
            return Command(goto="hil_wait")
        tasks = self.task_db.get_tasks_by_batch_id(self.tasks_batch_id)
        human_tasks = list([t for t in tasks if t.state == State.HUMAN])

        if not human_tasks:
            print("No tasks require human approval, skipping HIL")
            return Command(goto="incident_agent")

        print(f"Preparing questions for {len(human_tasks)} tasks")

        # Store that we're about to send questions for these task IDs
        batch_key = f"hil_batch_{self.tasks_batch_id}"
        self.db.client["workflow_status"]["hil_process"].update_one(
            {"batch_id": str(self.tasks_batch_id)},
            {"$set": {
                "preparing": True,
                "task_count": len(human_tasks),
                "task_ids": [str(t.id) for t in human_tasks]
            }},
            upsert=True
        )

        # Check which tasks already have questions
        questions_to_send = []
        for task in human_tasks:
            existing_questions = list(self.db.client["question_db"]["questions"].find({"task_id": str(task.id)}))
            if not existing_questions:
                questions_to_send.append(task)

        if questions_to_send:
            print(f"Sending {len(questions_to_send)} new questions")
            for task in questions_to_send:
                self.hil_ask_yesno(
                    self.incident.id,
                    f"""
                    *CISO Agent* wants to know if the command proposed by Sysadmin Expert is *safe to execute*.
                    Command: `{task.command}`
                    Reason: {task.reason}
                    Additional comments: {task.comments}

                    Do you approve it?
                    """,
                    task.id,
                )
        else:
            print("All required questions are already sent")

        # Mark preparation as complete
        self.db.client["workflow_status"]["hil_process"].update_one(
            {"batch_id": str(self.tasks_batch_id)},
            {"$set": {"preparing": False, "waiting": True}}
        )

        # Now route to the waiting node
        return Command(goto="hil_wait")

    def hil_wait_node(self, state: Messages):
        """Only handles the interrupt/wait part"""
        print("Interrupting workflow to wait for human responses")
        value = interrupt("waiting for human in the loop")

        # After resuming, mark that we're no longer waiting
        self.db.client["workflow_status"]["hil_process"].update_one(
            {"batch_id": str(self.tasks_batch_id)},
            {"$set": {"waiting": False, "resumed": True}}
        )

        print("Workflow resumed after human input")
        return Command(goto="nil_prepare")

    def schedule_task_for_execution(self,incident_id: str, batch_id: str, task_id: str):
        """Schedule a task for execution"""
        print(f"Scheduling task for execution: {task_id} for batch {batch_id}")
        task = self.task_db.get_task(task_id)
        task.state = State.APPROVED
        task.batch_id = batch_id
        task.id=None
        self.task_db.create_task(task)


        # After resuming, mark that we're no longer waiting
        self.db.client["workflow_status"]["hil_process"].update_one(
            {"batch_id": str(self.tasks_batch_id)},
            {"$set": {"waiting": False, "resumed": True}},
        )

        print("Workflow resumed after human input")
        return Command(goto="incident_agent")

    def run(self, incident_id: str, task_ids: List[str], q_ids: List[str] = []):
        incident = self.incident_db.get_incident(incident_id)
        self.incident = incident
        self.instance = self.inventory_db.get_instance(incident.instance_id)
        self.tasks_batch_id = uuid4()

        host_info = (
            f"OS: {self.instance.metadata.host_info.os}, "
            f"Platform: {self.instance.metadata.host_info.platform}, "
            f"Platform Family: {self.instance.metadata.host_info.platform_family}, "
            f"Platform Version: {self.instance.metadata.host_info.platform_version}, "
            f"Kernel Version: {self.instance.metadata.host_info.kernel_version}"
        )

        # Ensure incident ID is prominently featured in any message construction
        if not task_ids and not q_ids:
            message = (
                f"## Incident Details\n"
                f"- **Incident ID**: {incident.id}\n"
                f"- **Node ID**: {incident.instance_id}\n"
                f"- **Type**: {incident.type}\n"
                f"- **Status**: {incident.status}\n"
                f"- **Tasks Batch ID**: {self.tasks_batch_id}\n\n"
                f"## Host Information\n"
                f"{host_info}\n\n"
                f"## Incident Data\n"
                f"{incident.data}\n\n"
                f"Address this incident with ID {incident.id}. You must use this exact incident ID in all tools."
            )
        elif q_ids:
            message = f"## Incident ID: {incident.id}\n\nFollowing answers have come from the user: \n\n"
            for q_id in q_ids:
                q = question_db.get_question(q_id)
                message +=  (
                    f"Question: {q.question}\nAnswer: {q.response}, task: {q.task_id}\n\n"
                )
                if q.response and q.response.lower() == "yes":
                    self.schedule_task_for_execution(incident.id, self.tasks_batch_id, q.task_id)
            message += f"Please continue with the incident {incident.id}. Please verify if confirmed tasks are executed and if they were solve the incident."

        else:
            outputs = []
            for task_id in task_ids:
                task = self.task_db.get_task(task_id)
                outputs.append(
                    {"task_id": task.id, "command": task.command, "output": task.output}
                )

            message = (
                f"## Task Execution Results\n"
                f"- **Incident ID**: {incident.id}\n"
                f"- **Tasks Batch ID**: {self.tasks_batch_id}\n\n"
                f"All tasks are done. Here are the results in dict format:\n\n"
                f"{outputs}\n\n"
                f"To create new tasks use new batch id: {self.tasks_batch_id}"
            )

        try:
            events = self.network.stream(
                {
                    "messages": [{"role": "user", "content": message}],
                },
                config={
                    "configurable": {"thread_id": str(incident.id)},
                    "callbacks": [lf_handler],
                    "recursion_limit": self.recursion_limit
                },
            )

            # Add defensive error handling for event processing
            for event in events:
                try:
                    for agent, ev2 in event.items():
                        if isinstance(ev2, dict) and "messages" in ev2 and ev2["messages"]:
                            print(agent)
                            try:
                                ev2["messages"][-1].pretty_print()
                            except (AttributeError, IndexError):
                                print(f"Message format error: {ev2['messages']}")
                            print("---------------------\n\n")
                        else:
                            print(f"{agent}: {ev2}")
                except Exception as e:
                    print(f"Error processing event: {e}, event: {event}")
        except Exception as e:
            print(f"Error in graph execution: {e}")

    def update_status(
        self,
        incident_id: Annotated[str, "incident id (uuid)"],
        content: Annotated[str, "message content, markdown enabled"],
    ) -> Annotated[bool, "True if the comment was successful, False otherwise"]:
        """Make a comment on ITSM ticket related to the incident
        Returns timestamp of a message"""

        print(f"Updating status for incident {incident_id} with content: {content}")

        # check if thread is is in db
        if not self.hil_integration:
            return False

        inc = self.incident_db.get_incident(incident_id)
        if not inc.thread_id:
            inc.thread_id = self.hil_integration.write_message(content)
            self.incident_db.update_incident(inc)
        else:
            self.hil_integration.write_message(content, inc.thread_id)

        return True

    def hil_ask_yesno(
        self,
        incident_id: Annotated[str, "incident id (uuid)"],
        question: Annotated[str, "question to ask, must be answered with yes or no"],
        t_id: Annotated[str, "task id (uuid)"],
    ):
        """Ask a question to a human operator, expecting a yes or no answer."""
        if not self.hil_integration:
            return False

        existing_q = list(question_db.questions.find({"task_id": str(t_id)}))
        if existing_q:
            print(f"Question for task {t_id} already exists, not sending duplicate")
            return True

        inc = self.incident_db.get_incident(incident_id)
        if not inc.thread_id:
            return False

        q = Question(
            id=None,
            question=question,
            type="yesno",
            incident_id=incident_id,
            thread_ts=inc.thread_id,
            task_id=t_id,
        )
        q = question_db.create_question(q)

        resp = self.hil_integration.yesno(question, q.id, inc.thread_id)
        q.question_ts = resp

        question_db.update_question(q)

        return True

    def resume_after_execution(self, batch_id: str, task_ids: List[str]):
        """Resume workflow after task execution completes"""
        # Get the workflow state that was saved before interrupt
        workflow_state = self.db.client["workflow_status"]["nil_process"].find_one(
            {"batch_id": str(batch_id)}
        )

        if not workflow_state or not workflow_state.get("incident_id"):
            print(f"ERROR: Cannot resume workflow - missing incident ID for batch {batch_id}")
            return

        # Restore incident context
        incident_id = workflow_state["incident_id"]
        incident = self.incident_db.get_incident(incident_id)

        if not incident:
            print(f"ERROR: Cannot resume workflow - incident {incident_id} not found")
            return

        self.incident = incident
        self.instance = self.inventory_db.get_instance(incident.instance_id)
        self.tasks_batch_id = UUID(batch_id)

        # Get output for the tasks
        outputs = []
        for task_id in task_ids:
            task = self.task_db.get_task(task_id)
            outputs.append({"task_id": task.id, "command": task.command, "output": task.output})

        # Create a clear message with the incident ID prominently displayed
        message = (
            f"## Task Execution Results\n"
            f"- **Incident ID**: {incident.id}\n"
            f"- **Tasks Batch ID**: {batch_id}\n\n"
            f"Task execution complete. Here are the results:\n\n"
            f"{outputs}\n\n"
            f"Continue addressing incident {incident.id}."
        )

        # Resume the workflow
        try:
            # Resume with explicit incident ID to ensure it's available
            thread_config = {
                "recursion_limit": self.recursion_limit,  # Move recursion_limit here
                "configurable": {"thread_id": str(incident.id)}
            }
            self.network.invoke(
                {
                    "messages": [{"role": "user", "content": message}]
                },
                config=thread_config
            )
        except Exception as e:
            print(f"Error resuming workflow: {e}")

    def _preserve_incident_context(self, state: MessagesState) -> MessagesState:
        """Ensure the incident ID is included in context exchanges between agents"""
        if not hasattr(self, 'incident') or not self.incident:
            return state

        # Always include the incident ID in all agent communications
        incident_context = f"Incident ID: {self.incident.id}\n"

        # Add context to each message
        new_messages = []
        for msg in state["messages"]:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                # Only add context if it's not already there
                if not msg.content.startswith(incident_context):
                    msg.content = incident_context + msg.content
            new_messages.append(msg)

        return {"messages": new_messages}

@tool
def create_task(task: Task):
    """Create a task in the TaskDB."""
    if not task.state:
        task.state = State.CREATED
    return task_db.create_task(task)


@tool
def list_tasks(incident_id: str):
    """List all pending approval tasks."""
    return task_db.get_tasks_by_incident_id(incident_id, state=State.CREATED)


@tool
def change_task(
    id: Annotated[str, "task id (uuid)"],
    state: Annotated[State, "approval decision as State (approved, rejected, human)"],
    comment: Annotated[Optional[str], "comment to add to the task"] = None,
):
    """Approve or reject a task."""
    if comment is not None:
        task_db.add_comment(id, comment)
    return task_db.update_state(id, state)


@tool
def close_incident(incident_id: str):
    """Close an incident."""
    return incident_db.update_status(incident_id, Status.CLOSED)
