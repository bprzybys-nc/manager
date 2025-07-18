import unittest
import json
import os

from fastapi.testclient import TestClient

from sysaidmin.manager.src.usecases.db_incident_assistant.app.api import app

class TestDBIncidentAssistantAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)


    def test_ping(self):
        """Test that the ping endpoint works correctly"""
        response = self.client.get("/public/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "pong"})

    def test_trigger_incident_with_valid_data(self):
        """Test that the incident endpoint works correctly with valid data"""
        # Load sample alert data from the JSON file
  
        # Get the path to the sample alert JSON file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sample_alert_path = os.path.join(current_dir, "sample_alert.json")
        
        # Load the sample alert data
        with open(sample_alert_path, "r") as f:
            sample_alert_data = json.load(f)
            
        # Convert the data to a string as expected by the endpoint
        # Test with the sample alert data
        response = self.client.post("/public/incidents", json=sample_alert_data)
        self.assertEqual(response.status_code, 200)

    def temp_test_get_all_instances(self):
        """Test that the get all instances endpoint works correctly"""
        response = self.client.get("/public/instances")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()