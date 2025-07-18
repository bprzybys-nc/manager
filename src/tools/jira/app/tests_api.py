import os
import sys
import unittest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load environment variables from a .env file for local testing
# This makes it easier to run tests without manually setting env vars.
load_dotenv(override=True)

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.tools.jira.app.api import app


class TestJiraAPIIntegration(unittest.TestCase):
    """
    Integration test suite for the Jira Tool's FastAPI endpoints.

    NOTE: These tests make REAL calls to the Jira API and require valid
    JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN to be set in the environment.
    """

    def setUp(self):
        """Set up the test client and verify environment variables before each test."""
        self.client = TestClient(app)

        # Print environment variables for debugging
        print("\nEnvironment Variables:")
        print(f"JIRA_URL: {os.getenv('JIRA_URL')}")
        print(f"JIRA_USERNAME: {os.getenv('JIRA_USERNAME')}")

        # Ensure that the required environment variables are available for the tests.
        self.assertIsNotNone(os.getenv("JIRA_URL"), "JIRA_URL environment variable not set.")
        self.assertIsNotNone(os.getenv("JIRA_USERNAME"), "JIRA_USERNAME environment variable not set.")
        self.assertIsNotNone(os.getenv("JIRA_API_TOKEN"), "JIRA_API_TOKEN environment variable not set.")

    def test_add_jira_comment_real(self):
        """Tests adding a comment to a real Jira issue."""
        # Arrange: Use a real, existing Jira issue ID for this test.
        # IMPORTANT: Change this to a valid issue ID in your test project.
        ticket_id = "OVR-111"
        comment_text = f"This is a real comment added by an integration test at {__name__}."

        # Act: Make a POST request to the live endpoint.
        response = self.client.post(
            f"/tickets/{ticket_id}/comments",
            json={"comment": comment_text}
        )

        # Assert: Check for a successful response from the server.
        # If the status code is not 200, the message will include the server's response text.
        self.assertEqual(
            response.status_code, 
            200, 
            f"API returned non-200 status. Response: {response.text}"
        )
        self.assertEqual(response.json(), {"message": "Comment added successfully"})

    def test_add_jira_comment_with_formatting_real(self):
        """Tests adding a formatted (code) comment to a real Jira issue."""
        # Arrange
        ticket_id = "OVR-111"
        comment_text = "This is a real formatted comment with code."

        # Act
        response = self.client.post(
            f"/tickets/{ticket_id}/comments",
            json={"comment": comment_text, "formatting": "code"}
        )

        # Assert
        self.assertEqual(
            response.status_code, 
            200, 
            f"API returned non-200 status. Response: {response.text}"
        )
        self.assertEqual(response.json(), {"message": "Comment added successfully"})

    def test_get_jira_details_real(self):
        """Tests retrieving details (description and comments) from a real Jira issue."""
        # Arrange: Use a real, existing Jira issue ID for this test.
        ticket_id = "OVR-111"  # IMPORTANT: Use an issue that has a description and comments.

        # Act: Make a GET request to the new endpoint.
        response = self.client.get(f"/tickets/{ticket_id}")

        # Assert: Check for a successful response and correct structure.
        self.assertEqual(
            response.status_code, 
            200, 
            f"API returned non-200 status. Response: {response.text}"
        )
        
        data = response.json()
        self.assertIn("description", data)
        self.assertIn("comments", data)
        self.assertIsInstance(data["comments"], list)

        # Optional: Print the details for verification
        print(f"\n--- Details for {ticket_id} ---")
        print(f"Description: {data['description']}")
        print(f"Comments ({len(data['comments'])}):\n" + "\n".join(data['comments']))
        print("-------------------------")

    @unittest.skip("Skipping closing ticket test to prevent accidental modifications.")
    def test_close_jira_ticket_real(self):
        """
        Tests closing a real Jira issue.
        WARNING: This test will actually attempt to transition a ticket's status.
        Enable this test with caution and use a dedicated test issue.
        """
        # Arrange
        ticket_id = "OVR-111"  # IMPORTANT: Use a valid test issue in an appropriate state.
        comment_text = "Closing ticket via integration test."

        # Act
        response = self.client.put(
            f"/tickets/{ticket_id}",
            json={"comment": comment_text}
        )

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Ticket closed successfully"})


if __name__ == "__main__":
    unittest.main()

