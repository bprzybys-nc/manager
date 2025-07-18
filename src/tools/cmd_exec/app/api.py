import os
import sys
from typing import Optional, List, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
import certifi
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.modules.task.db import TaskDB
from src.modules.tools.data_objects import ProcessedCommand

from src.tools.cmd_exec.app.cmd_exec import CommandExecutorTool, UnixExecutionPlatform

app = FastAPI()

connection_string = os.environ.get('MONGODB_URI')
db_client = MongoClient(connection_string, tlsCAFile=certifi.where())
task_db = TaskDB(db_client)

class RunCommandsRequest(BaseModel):
    incident_id: Optional[str] = None
    instance_id: Optional[str] = None
    commands: Optional[List[ProcessedCommand]] = None
    response_endpoint: Optional[str] = None
    command_types: Optional[List[str]] = None

    
def unix_execution_finished_callback(incident_id: str, response_endpoint: str, execution_results: Dict[str, str]):
    print(f"Incident ID: {incident_id}")
    print(f"Execution results: {execution_results}")
    print(f"Response endpoint: {response_endpoint}")

    response = requests.post(response_endpoint, json={"incident_id": incident_id, "execution_results": execution_results})
    print(f"[UnixExecutionFinishedCallback] Response: {response}")




unix_execution_platform = UnixExecutionPlatform(task_db)
unix_execution_tool = CommandExecutorTool(unix_execution_platform, unix_execution_finished_callback)

@app.post("/confirmations")
def response_endpoint(data: dict):
    print(f"Confirmations: {data}")
    incident_id = data["incident_id"]
    tasks_done_list=data["tasks_done"]
    print(f"Incident ID: {incident_id}")
    print(f"Tasks done: {tasks_done_list}")

    tasks = task_db.get_tasks_by_incident_id(incident_id)
    dict={}
    for task in tasks:
        if str(task.id) in tasks_done_list:
            dict[task.command] = task.output
    
    unix_execution_platform.commands_executed(incident_id, dict)
    return {"status": "received"}

@app.post("/executions")
def execute(request: RunCommandsRequest):
    print(f"Executing request: {request}")
    unix_execution_tool.run(request.incident_id, request.instance_id, request.commands,request.response_endpoint, request.command_types)
    return {"message": "Commands scheduled for execution successfully!"}

