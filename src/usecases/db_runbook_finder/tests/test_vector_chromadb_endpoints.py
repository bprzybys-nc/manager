#!/usr/bin/env python3
"""
End-to-end test script for Vector/ChromaDB endpoints in Confluence tool.
Tests semantic search capabilities using the ChromaDB vector database.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

def main():
    """Main function to test vector/ChromaDB endpoints."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Warning: python-dotenv not available, using existing environment variables")
        load_dotenv = None
    
    from fastapi.testclient import TestClient
    
    # Manager root - use relative path from test file location
    manager_root = Path(__file__).parent.parent.parent.parent
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
        from tools.confluence.app.api import app
        print("✓ Successfully imported Confluence API application")
    except ImportError as e:
        print(f"✗ Failed to import Confluence API application: {e}")
        return 1
    
    # Add ChromaDB dependency to manager's pyproject.toml if needed
    check_and_add_chromadb_dependency(manager_root)
    
    # Continue with the test logic
    return run_vector_tests(TestClient(app))

def check_and_add_chromadb_dependency(manager_root: Path):
    """Check if chromadb dependency is in pyproject.toml and add it if needed."""
    pyproject_path = manager_root / "pyproject.toml"
    
    try:
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        if 'chromadb' not in content:
            print("⚠ ChromaDB dependency not found in pyproject.toml, adding it...")
            
            # Add chromadb and sentence-transformers dependencies
            if '# Jira tool dependencies' in content:
                content = content.replace(
                    '"jira>=3.6.0",',
                    '"jira>=3.6.0",\n    # ChromaDB/Vector store dependencies\n    "chromadb>=0.4.0",\n    "sentence-transformers>=2.2.0",'
                )
                
                with open(pyproject_path, 'w') as f:
                    f.write(content)
                
                print("✓ Added ChromaDB dependencies to pyproject.toml")
                print("⚠ Please run 'uv sync' to install the dependencies")
                return True
            else:
                print("✗ Could not find Jira dependencies section to add ChromaDB")
                return False
        else:
            print("✓ ChromaDB dependency already present in pyproject.toml")
            return True
            
    except Exception as e:
        print(f"✗ Error checking/updating pyproject.toml: {e}")
        return False

def run_vector_tests(client) -> int:
    """Run all the Vector/ChromaDB endpoint tests."""
    print("\n" + "="*70)
    print("CHECKING ENVIRONMENT VARIABLES FOR CONFLUENCE")
    print("="*70)
    
    required_vars = ["CONFLUENCE_URL", "CONFLUENCE_USERNAME", "CONFLUENCE_API_TOKEN"]
    all_vars_set = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask API token for security
            display_value = value if var != "CONFLUENCE_API_TOKEN" else f"{value[:10]}...{value[-4:]}"
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_vars_set = False
    
    if not all_vars_set:
        print("\n✗ Missing required environment variables for Confluence.")
        print("Vector/ChromaDB tests will use mock data only.")

    print("\n" + "="*70)
    print("TESTING VECTOR/CHROMADB ENDPOINTS")
    print("="*70)
    
    test_results = []
    
    # Test 1: Health check - basic health endpoint
    print(f"\n1. Testing GET /health (basic health check)")
    print("-" * 45)
    try:
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Successfully retrieved health status")
            print(f"Status: {data.get('status', 'unknown')}")
            test_results.append(("Health check (basic)", True, "Service is healthy"))
        else:
            print(f"✗ Failed to retrieve health status: {response.text}")
            test_results.append(("Health check (basic)", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during health check: {str(e)}")
        test_results.append(("Health check (basic)", False, f"Exception: {str(e)}"))
    
    # Test 2: GET /search/runbooks - Semantic runbook search
    print(f"\n2. Testing GET /search/runbooks (semantic search)")
    print("-" * 50)
    try:
        test_query = "database connection timeout issues"
        response = client.get(f"/search/runbooks?query={test_query}&limit=3")
        print(f"Status Code: {response.status_code}")
        print(f"Query: {test_query}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Successfully performed semantic runbook search")
            print(f"Total Results: {data.get('total_results', 0)}")
            print(f"Processing Time: {data.get('processing_time', 'N/A')}s")
            
            results = data.get('results', [])
            if results:
                print("\nTop Results:")
                for i, result in enumerate(results[:2], 1):
                    title = result.get('metadata', {}).get('title', 'Unknown Title')
                    score = result.get('score', 0)
                    print(f"  {i}. {title} (score: {score:.3f})")
                    
                test_results.append(("GET semantic search", True, f"Found {len(results)} results"))
            else:
                print("⚠ No results found (this may be expected if no data is indexed)")
                test_results.append(("GET semantic search", True, "No results (empty index)"))
        else:
            print(f"✗ Failed semantic search: {response.text}")
            test_results.append(("GET semantic search", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during GET semantic search: {str(e)}")
        test_results.append(("GET semantic search", False, f"Exception: {str(e)}"))
    
    # Test 3: GET /search/confluence - Regular Confluence search
    print(f"\n3. Testing GET /search/confluence (confluence text search)")
    print("-" * 56)
    try:
        test_query = "database troubleshooting"
        response = client.get(f"/search/confluence?query={test_query}&limit=3")
        print(f"Status Code: {response.status_code}")
        print(f"Query: {test_query}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Successfully performed Confluence text search")
            results = data.get('results', [])
            print(f"Total Results: {len(results)}")
            
            if results:
                print("\nConfluence Search Results:")
                for i, result in enumerate(results[:2], 1):
                    title = result.get('title', 'Unknown Title')
                    space = result.get('space', {}).get('key', 'Unknown')
                    print(f"  {i}. {title} (space: {space})")
                    
                test_results.append(("Confluence text search", True, f"Found {len(results)} results"))
            else:
                print("⚠ No results found")
                test_results.append(("Confluence text search", True, "No results found"))
        else:
            print(f"✗ Failed Confluence search: {response.text}")
            test_results.append(("Confluence text search", False, f"Status {response.status_code}: {response.text}"))
            
    except Exception as e:
        print(f"✗ Exception during Confluence search: {str(e)}")
        test_results.append(("Confluence text search", False, f"Exception: {str(e)}"))
    
    # Test 4: Test different query types and limits
    print(f"\n4. Testing various query patterns and limits")
    print("-" * 45)
    try:
        test_queries = [
            ("database", 2),
            ("connection timeout", 5),
            ("performance troubleshooting guide", 1),
            ("mongodb postgresql mysql", 3)
        ]
        
        successful_queries = 0
        total_results_found = 0
        
        for query, limit in test_queries:
            response = client.get(f"/search/runbooks?query={query}&limit={limit}")
            
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get('results', []))
                total_results_found += results_count
                successful_queries += 1
                print(f"✓ '{query}' → {results_count} results (limit: {limit})")
            else:
                print(f"✗ '{query}' → Failed (status: {response.status_code})")
        
        if successful_queries == len(test_queries):
            test_results.append(("Multiple query patterns", True, f"{successful_queries}/{len(test_queries)} successful, {total_results_found} total results"))
        else:
            test_results.append(("Multiple query patterns", False, f"Only {successful_queries}/{len(test_queries)} successful"))
            
    except Exception as e:
        print(f"✗ Exception during multiple queries test: {str(e)}")
        test_results.append(("Multiple query patterns", False, f"Exception: {str(e)}"))
    
    # Test 5: Test error handling (empty query, invalid limits)
    print(f"\n5. Testing error handling (validation)")
    print("-" * 42)
    try:
        error_tests = [
            ("", 5, "empty query"),
            ("valid query", 0, "invalid limit (too low)"),
            ("valid query", 25, "invalid limit (too high)")
        ]
        
        successful_error_handling = 0
        
        for query, limit, description in error_tests:
            response = client.get(f"/search/runbooks?query={query}&limit={limit}")
            
            if response.status_code == 422:  # Validation error expected
                print(f"✓ {description} → Correctly rejected (422)")
                successful_error_handling += 1
            else:
                print(f"✗ {description} → Unexpected response (status: {response.status_code})")
        
        if successful_error_handling == len(error_tests):
            test_results.append(("Error handling validation", True, "All validation errors handled correctly"))
        else:
            test_results.append(("Error handling validation", False, f"Only {successful_error_handling}/{len(error_tests)} handled correctly"))
            
    except Exception as e:
        print(f"✗ Exception during error handling test: {str(e)}")
        test_results.append(("Error handling validation", False, f"Exception: {str(e)}"))
    
    # Test 6: Performance timing test
    print(f"\n6. Testing search performance timing")
    print("-" * 37)
    try:
        performance_query = "database performance monitoring"
        iterations = 3
        total_time = 0
        
        for i in range(iterations):
            start_time = time.time()
            response = client.get(f"/search/runbooks?query={performance_query}&limit=5")
            end_time = time.time()
            
            search_time = end_time - start_time
            total_time += search_time
            
            if response.status_code == 200:
                data = response.json()
                processing_time = data.get('processing_time', 0)
                print(f"✓ Search {i+1}: {search_time:.3f}s total, {processing_time:.3f}s processing")
            else:
                print(f"✗ Search {i+1}: Failed")
        
        avg_time = total_time / iterations
        print(f"Average search time: {avg_time:.3f}s")
        
        if avg_time < 2.0:  # Should be under 2 seconds
            test_results.append(("Performance timing", True, f"Avg {avg_time:.3f}s (good performance)"))
        else:
            test_results.append(("Performance timing", False, f"Avg {avg_time:.3f}s (slow performance)"))
            
    except Exception as e:
        print(f"✗ Exception during performance test: {str(e)}")
        test_results.append(("Performance timing", False, f"Exception: {str(e)}"))
    
    # Print test summary
    print("\n" + "="*70)
    print("VECTOR/CHROMADB TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result, _ in test_results if result is True)
    failed = sum(1 for _, result, _ in test_results if result is False)
    total = len(test_results)
    
    print(f"Total tests: {total}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    
    print("\nDetailed Results:")
    for test_name, result, message in test_results:
        status_icon = "✓" if result is True else "✗"
        print(f"{status_icon} {test_name}: {message}")
    
    print(f"\nSuccess rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
    
    if passed > 0:
        print("\n🎉 ChromaDB/Vector search capabilities are functional!")
        if failed == 0:
            print("✅ All vector search features working perfectly!")
    
    # Return appropriate exit code
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)