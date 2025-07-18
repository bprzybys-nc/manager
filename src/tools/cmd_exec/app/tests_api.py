import unittest
import os
import sys
import uuid
from fastapi.testclient import TestClient


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))


from src.tools.cmd_exec.app.api import app
from src.tools.cmd_exec.app.cmd_exec import ProcessedCommand


class TestDBIncidentAssistantAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_execute_commands(self):

        
        # Original Python test code
        command = ProcessedCommand(command="top -b|head -n 10",platform="shell")
        json_command = command.model_dump()
#27e36587-84ad-4bdd-a84b-91f76919aff8
        incident_id = "27e36587-84ad-4bdd-a84b-91f76919aff8"
        instance_id = "66f7c2d7-536e-439f-9f9c-394357c91248"

        response = self.client.post("/executions", json={"incident_id": incident_id, "instance_id": instance_id, "commands": [json_command],"command_types":["shell"]})
        print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Commands executed successfully!"})




if __name__ == "__main__":
    unittest.main()