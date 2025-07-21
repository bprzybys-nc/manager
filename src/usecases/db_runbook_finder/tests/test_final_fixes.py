#!/usr/bin/env python3
"""
Quick test to identify why validation errors return 500 instead of 422.
"""

import os
import sys
import json
from pathlib import Path

def main():
    """Test specific validation scenarios to debug error handling."""
    
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Warning: python-dotenv not available")
        load_dotenv = None
    
    from fastapi.testclient import TestClient
    
    # Manager root setup
    manager_root = Path("/Users/bprzybysz/nc-src/ovora/manager")
    env_file = manager_root / ".env"
    
    if env_file.exists() and load_dotenv:
        load_dotenv(env_file, override=True)
    
    sys.path.insert(0, str(manager_root / "src"))
    
    from tools.confluence.app.api import app
    client = TestClient(app)
    
    print("Testing validation error scenarios...")
    
    # Test 1: Empty query parameter  
    print("\\n1. Testing empty query parameter")
    response = client.get("/search/runbooks?query=&limit=5")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    # Test 2: Invalid limit (too low)
    print("\\n2. Testing invalid limit (too low)")
    response = client.get("/search/runbooks?query=test&limit=0")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    # Test 3: Invalid limit (too high)
    print("\\n3. Testing invalid limit (too high)")
    response = client.get("/search/runbooks?query=test&limit=25")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    # Test 4: Empty runbook ID (tricky - FastAPI path parameter)
    print("\\n4. Testing empty runbook ID")
    # This is the tricky one - FastAPI might not even route empty path parameters
    response = client.get("/runbooks/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)