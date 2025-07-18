import os
import sys
import certifi
import traceback
from pymongo import MongoClient
from fastapi import FastAPI, Request

from src.usecases.db_incident_assistant.app.main import DBIncidentAssistant
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from src.modules.incident.db import IncidentDB, Incident, Type, Status
from src.modules.inventory.db import InventoryDB, InstanceStatus

app = FastAPI()

connection_string = os.environ.get('MONGODB_URI')
db_client = MongoClient(connection_string, tlsCAFile=certifi.where())
incident_db = IncidentDB(db_client)
inventory_db = InventoryDB(db_client)

db_incident_assistant = DBIncidentAssistant()

@app.post("/public/incidents")
def trigger_incident(incident: dict):
    print(f"Incident triggered: {incident}")
    # Extract the required fields
    try:
        incident_description = incident.get("body")
        hostname = incident.get("hostname")
        title = incident.get("title")

        instances = inventory_db.get_instances()
        print(f"Instances: {instances}")
        instance = find_instances_by_hostname(instances, hostname)
        if instance:
            incident=Incident(
                instance_id=instance.id,
                status=Status.OPEN,
                type=Type.OTHER,
                data=incident_description,
                response_endpoint=os.environ.get('CMD_EXEC_RESPONSE_ENDPOINT')
            )
            incident_db.create_incident(incident)

            host_description=', '.join(f"{k.replace('_', ' ').title()}: {getattr(instance.metadata.host_info, k)}" for k in vars(instance.metadata.host_info))

            db_incident_assistant.run(str(incident.id), str(instance.id), hostname, incident_description, host_description)
            return {"message": "Incident created successfully"}
        else:
            return {"message": "Instance not found"}
    except Exception as e:
        # Print the full traceback for debugging purposes
        traceback_str = traceback.format_exc()
        print(f"Full traceback:\n{traceback_str}")

        print(f"Error processing incident: {str(e)}")
        return {"message": f"Error processing incident: {str(e)}", "error": True}


@app.post("/confirmations")
def confirmations(confirmation: dict):
    print(f"Confirmation received: {confirmation}")

    if "correlation_id" in confirmation:
        print(f"Processing command confirmation for {confirmation['correlation_id']}")
        correlation_id=confirmation["correlation_id"]       
        approved=confirmation["approved"]
        db_incident_assistant.remediation_command_execution_confirmed(correlation_id, approved)
    elif "incident_id" in confirmation and "execution_results" in confirmation:
        print(f"Processing execution results for {confirmation['incident_id']}")
        incident_id=confirmation["incident_id"]
        execution_results=confirmation["execution_results"]

        db_incident_assistant.commands_execuction_finished(incident_id, execution_results)

    return {"message": "Confirmation received"}

@app.get("/public/instances")
def get_all_instances():
    instances = inventory_db.get_instances()
    count=0
    for instance in instances:
        print(f"Instance {count}: {instance.model_dump()}")
        count+=1
    return [instance.model_dump() for instance in instances]

@app.get("/public/ping")
def ping():
    return {"message": "pong"}


def find_instances_by_hostname(instances, target_hostname):
    print(f"Searching for instance with hostname: {target_hostname}")
    for instance in instances:
        print(f"Instance: {instance.model_dump()}")
        if instance.metadata:
            metadata = instance.metadata
            host_info = metadata.host_info
            if host_info and host_info.hostname == target_hostname:
                if instance.status == InstanceStatus.ACTIVE:
                    print(f"Instance found: {instance.id}")
                    return instance
                else:
                    print(f"Instance found {instance.id} for hostname {target_hostname} but it is not active.")
    
    return None