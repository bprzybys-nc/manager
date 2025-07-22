#!/usr/bin/env python3
"""
End-to-end test script for Jira endpoints using ticket AGENT-6.
This script tests all Jira API endpoints with real API calls.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def main_internal():
    """Internal main function that runs with proper dependencies."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Warning: python-dotenv not available, using existing environment variables")
        load_dotenv = None
    
    from fastapi.testclient import TestClient
    
    # Manager root is always /Users/bprzybysz/nc-src/ovora/manager
    manager_root = Path("/Users/bprzybysz/nc-src/ovora/manager")
    env_file = manager_root / ".env"
    
    # Load environment variables from .env file
    if env_file.exists() and load_dotenv:
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment variables from: {env_file}")
    elif env_file.exists():
        print(f"✓ Found .env file at: {env_file} (using existing environment variables)")
    else:
        print(f"✗ .env file not found at: {env_file}")
        return 1

    # Add the manager src directory to Python path
    sys.path.insert(0, str(manager_root / "src"))

    try:
        from tools.jira.app.api import app
        print("✓ Successfully imported Jira API application")
    except ImportError as e:
        print(f"✗ Failed to import Jira API application: {e}")
        print(f"Looking for module at: {manager_root / 'src' / 'tools' / 'jira' / 'app' / 'api.py'}")
        return 1
    
    # Continue with the rest of the test logic
    return run_tests(TestClient(app))

def run_tests(client):
    """Run all the Jira endpoint tests."""
    print("\n" + "="*60)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = ["JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"]
    all_vars_set = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask API token for security
            display_value = value if var != "JIRA_API_TOKEN" else f"{value[:10]}...{value[-4:]}"
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_vars_set = False
    
    if not all_vars_set:
        print("\n✗ Missing required environment variables. Please check your .env file.")
        return 1

    print("\n" + "="*60)
    print("TESTING JIRA ENDPOINTS WITH AGENT-6")
    print("="*60)
    
    ticket_id = "AGENT-6"
    test_results = []
    
    # Test 1: Get ticket details
    print(f"\n1. Testing GET /tickets/{ticket_id}")
    print("-" * 40)
    try:
        response = client.get(f"/tickets/{ticket_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Successfully retrieved ticket details")
            print(f"Description: {data.get('description', 'None')}")
            print(f"Comments count: {len(data.get('comments', []))}")
            
            # Display comments if any
            comments = data.get('comments', [])
            if comments:
                print("\nComments:")
                for i, comment in enumerate(comments[:3], 1):  # Show first 3 comments
                    print(f"  {i}. {comment[:100]}{'...' if len(comment) > 100 else ''}")
                if len(comments) > 3:
                    print(f"  ... and {len(comments) - 3} more comments")
            
            test_results.append(("GET ticket details", True, "Success"))
        else:
            print(f"✗ Failed to retrieve ticket details: {response.text}")
            test_results.append(("GET ticket details", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during GET request: {str(e)}")
        test_results.append(("GET ticket details", False, f"Exception: {str(e)}"))
    
    # Test 2: Add a comment (without formatting)
    print(f"\n2. Testing POST /tickets/{ticket_id}/comments (no formatting)")
    print("-" * 55)
    try:
        comment_text = "Test comment from end-to-end test script - no formatting"
        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"comment": comment_text}
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Successfully added comment: {result}")
            test_results.append(("POST comment (no formatting)", True, "Success"))
        else:
            print(f"✗ Failed to add comment: {response.text}")
            test_results.append(("POST comment (no formatting)", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during POST comment: {str(e)}")
        test_results.append(("POST comment (no formatting)", False, f"Exception: {str(e)}"))
    
    # Test 3: Add a formatted comment (code formatting)
    print(f"\n3. Testing POST /tickets/{ticket_id}/comments (code formatting)")
    print("-" * 58)
    try:
        comment_text = "Test comment with code formatting from end-to-end test"
        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={
                "comment": comment_text,
                "formatting": "code"
            }
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Successfully added formatted comment: {result}")
            test_results.append(("POST comment (code formatting)", True, "Success"))
        else:
            print(f"✗ Failed to add formatted comment: {response.text}")
            test_results.append(("POST comment (code formatting)", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during POST formatted comment: {str(e)}")
        test_results.append(("POST comment (code formatting)", False, f"Exception: {str(e)}"))
    
    # Test 4: Add a bold formatted comment
    print(f"\n4. Testing POST /tickets/{ticket_id}/comments (bold formatting)")
    print("-" * 58)
    try:
        comment_text = "Test comment with bold formatting from end-to-end test"
        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={
                "comment": comment_text,
                "formatting": "bold"
            }
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Successfully added bold comment: {result}")
            test_results.append(("POST comment (bold formatting)", True, "Success"))
        else:
            print(f"✗ Failed to add bold comment: {response.text}")
            test_results.append(("POST comment (bold formatting)", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during POST bold comment: {str(e)}")
        test_results.append(("POST comment (bold formatting)", False, f"Exception: {str(e)}"))
    
    # Test 5: Verify comments were added by getting ticket details again
    print(f"\n5. Testing GET /tickets/{ticket_id} (verify comments added)")
    print("-" * 55)
    try:
        response = client.get(f"/tickets/{ticket_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            comments = data.get('comments', [])
            print(f"✓ Successfully retrieved updated ticket details")
            print(f"Total comments: {len(comments)}")
            
            # Look for our test comments
            test_comments_found = 0
            for comment in comments:
                if "end-to-end test" in comment.lower():
                    test_comments_found += 1
            
            print(f"Test comments found: {test_comments_found}")
            test_results.append(("GET updated ticket details", True, f"Found {test_comments_found} test comments"))
        else:
            print(f"✗ Failed to retrieve updated ticket details: {response.text}")
            test_results.append(("GET updated ticket details", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during GET updated details: {str(e)}")
        test_results.append(("GET updated ticket details", False, f"Exception: {str(e)}"))
    
    # Note: Skipping the close ticket test to avoid accidentally closing AGENT-6
    print(f"\n6. SKIPPING PUT /tickets/{ticket_id} (close ticket)")
    print("-" * 48)
    print("⚠ Skipping close ticket test to prevent accidental modification of AGENT-6")
    test_results.append(("PUT close ticket", None, "Skipped to prevent accidental closure"))
    
    # Print test summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result, _ in test_results if result is True)
    failed = sum(1 for _, result, _ in test_results if result is False)
    skipped = sum(1 for _, result, _ in test_results if result is None)
    total = len(test_results)
    
    print(f"Total tests: {total}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Skipped: {skipped}")
    
    print("\nDetailed Results:")
    for test_name, result, message in test_results:
        status_icon = "✓" if result is True else "✗" if result is False else "⚠"
        print(f"{status_icon} {test_name}: {message}")
    
    print(f"\nSuccess rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
    
    # Return appropriate exit code
    return 1 if failed > 0 else 0

def main():
    """Main function."""
    return main_internal()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)