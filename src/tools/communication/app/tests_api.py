
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from src.tools.communication.app.api import app


class TestCommunicationAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_send_message(self):
        response = self.client.post("/messages/", json={"message": "Test message"})
        print(f"Response: {response}")
        self.assertEqual(response.status_code, 200)
  

if __name__ == "__main__":
    unittest.main()