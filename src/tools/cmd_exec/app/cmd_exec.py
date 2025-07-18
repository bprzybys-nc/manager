import os
import sys

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, TypedDict
from uuid import uuid4, UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


from src.modules.task.db import CommandType, State, Task, TaskDB, Type
from src.modules.tools.data_objects import ProcessedCommand

class Platform(ABC):
    @abstractmethod
    def execute_commands(self, correlation_id: str, commands: List[str], command_type: str):
        pass

    @abstractmethod
    def add_commands_executed_callback(self, callback: Callable):
        pass


class UnixExecutionPlatform(Platform):
    """Used to communicate with agent running on unix based host."""

    def __init__(self, task_db: TaskDB):
        self.task_db = task_db
        self.commands_executed_callback = []

    def execute_commands(self, incident_id: str, instance_id: str, commands: List[str], command_types: List[str]):
        print(f"UnixExecutionPlatform execute_commands: {incident_id}, {instance_id}, {commands}, {command_types}")
        tasks = []
        task_batch_id = uuid4()
        for command, command_type in zip(commands, command_types):
            task = Task(
                incident_id= UUID(incident_id),
                instance_id= UUID(instance_id),
                c_type=CommandType.FIX,
                type=Type.PSQL if command_type == "psql" else Type.SHELL,    
                reason="Diagnostic",
                command=command,
                state=State.APPROVED,
                batch_id=task_batch_id,
            )
            self.task_db.create_task(task)
            tasks.append(task)

        self.task_db.create_batch_tasks(
            incident_id, task_batch_id, [t.id for t in tasks]
        )

    #this method will be called then commands executions are finished
    #all callback registered in add_commands_executed_callback will be called
    def commands_executed(self, incident_id: str, execution_results: Dict[str, str]):
        for callback in self.commands_executed_callback:
            callback(incident_id, execution_results)

    def add_commands_executed_callback(self, callback: Callable):
        self.commands_executed_callback.append(callback)

class ExucutionInputState(TypedDict):
    incident_id: str
    instance_id: str
    commands: List[str]
    response_endpoint: str  
    command_types: List[str]

class ExecutionOutputState(TypedDict):
    execution_results: Dict[str, str]
    response_endpoint: str

class ExecutionState(ExucutionInputState, ExecutionOutputState):
    pass

class CommandExecutorTool:
    """Abstraction used to execute on various platforms"""

    def __init__(
        self, execution_platform: Platform, execution_finished_callback: Callable = None
    ):
        self.execution_platform = execution_platform
        #execution_finished_callback will be called by self.commands_executed then commands executions are finished
        self.execution_finished_callback = execution_finished_callback
        #comands_executed will be called by platform when commands executions are finished
        self.execution_platform.add_commands_executed_callback(self.commands_executed)
        self.graph = self._build()

    def run(
        self, incident_id: str, instance_id: str, commands: List[ProcessedCommand] = [], response_endpoint: str = None, command_types: List[str] = None
    ):
        print(f"CommandExecutorTool run: {incident_id}, {instance_id}, {commands}, {response_endpoint}, {command_types}")
        thread_config = {"configurable": {"thread_id": incident_id}}
        self.graph.invoke(
            {
                "incident_id": incident_id,
                "instance_id": instance_id,
                "commands": [command.command for command in commands],
                "response_endpoint": response_endpoint,
                "command_types": command_types
            },
            config=thread_config,
        )

    def _build(self):
        checkpointer = MemorySaver()
        graph_builder = StateGraph(ExecutionState, input=ExucutionInputState, output=ExecutionOutputState)

        def execute_commands(state):
            if "incident_id" not in state:
                return state
            self.execution_platform.execute_commands(
                state["incident_id"], state["instance_id"], state["commands"], state["command_types"]
            )
            return state

        def wait_for_execution(state):
            if "commands" not in state:
                return state
            execution_results = interrupt(state["commands"])
            state["execution_results"] = execution_results
            return state

        graph_builder.add_node("execute_commands", execute_commands)
        graph_builder.add_node("wait_for_execution", wait_for_execution)

        graph_builder.add_edge(START, "execute_commands")
        graph_builder.add_edge("execute_commands", "wait_for_execution")
        graph_builder.add_edge("wait_for_execution", END)

        return graph_builder.compile(checkpointer=checkpointer)

    def commands_executed(self, incident_id: str, execution_results: Dict[str, str]):

        thread_config = {"configurable": {"thread_id": incident_id}}
        state = self.graph.get_state(thread_config)
        if state.created_at is None:
            return

        result = self.graph.invoke(
            Command(resume=execution_results), config=thread_config
        )
        self.execution_finished_callback(incident_id,result["response_endpoint"], result["execution_results"])

