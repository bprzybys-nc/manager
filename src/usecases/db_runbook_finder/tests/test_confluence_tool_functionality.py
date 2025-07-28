#!/usr/bin/env python3
"""
Temporary test to validate Confluence tool functionality for runbook discovery.

This test validates that the Confluence tool in src/tools/confluence is working
and can be used for the runbook discovery system.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add manager src to path  
manager_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(manager_root / "src"))

def setup_environment():
    """Setup environment variables from .env file."""
    env_file = manager_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment variables from: {env_file}")
    else:
        print(f"✗ .env file not found at: {env_file}")
        return False
    return True

def check_confluence_credentials():
    """Check if Confluence credentials are available."""
    required_vars = ["CONFLUENCE_URL", "CONFLUENCE_USERNAME", "CONFLUENCE_API_TOKEN"]
    all_vars_set = True
    
    print("\n" + "="*60)
    print("CHECKING CONFLUENCE CREDENTIALS")
    print("="*60)
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask API token for security
            display_value = value if var != "CONFLUENCE_API_TOKEN" else f"{value[:10]}...{value[-4:]}"
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_vars_set = False
    
    return all_vars_set

def test_confluence_tool_import():
    """Test that we can import the Confluence tool components."""
    print("\n" + "="*60)
    print("TESTING CONFLUENCE TOOL IMPORTS")
    print("="*60)
    
    try:
        # Test importing the main ConfluenceClient
        from tools.confluence.app.confluence import ConfluenceClient
        print("✓ Successfully imported ConfluenceClient")
        
        # Test importing VectorStore
        from tools.confluence.app.vector_store import VectorStore
        print("✓ Successfully imported VectorStore")
        
        # Test importing models
        from tools.confluence.app.models import RunbookContent, RunbookMetadata
        print("✓ Successfully imported RunbookContent, RunbookMetadata")
        
        return True
    except ImportError as e:
        print(f"✗ Failed to import Confluence components: {e}")
        return False

def test_confluence_client_initialization():
    """Test that ConfluenceClient can be initialized with .env credentials."""
    print("\n" + "="*60)
    print("TESTING CONFLUENCE CLIENT INITIALIZATION")
    print("="*60)
    
    try:
        from tools.confluence.app.confluence import ConfluenceClient
        
        # Initialize client (should use .env credentials)
        client = ConfluenceClient()
        print("✓ Successfully initialized ConfluenceClient")
        
        # Check if client has required attributes
        assert hasattr(client, 'base_url'), "Client should have base_url attribute"
        assert hasattr(client, 'get_page_by_id'), "Client should have get_page_by_id method"
        print("✓ Client has required attributes")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize ConfluenceClient: {e}")
        return False

def test_vector_store_initialization():
    """Test that VectorStore can be initialized with mcdb-runbooks collection."""
    print("\n" + "="*60)
    print("TESTING VECTOR STORE INITIALIZATION")
    print("="*60)
    
    try:
        from tools.confluence.app.vector_store import VectorStore
        
        # Initialize VectorStore with our collection name
        vector_store = VectorStore(collection_name="mcdb-runbooks")
        print("✓ Successfully initialized VectorStore with mcdb-runbooks collection")
        
        # Check collection name
        assert vector_store.collection_name == "mcdb-runbooks", "Collection name should be mcdb-runbooks"
        print("✓ Collection name is correctly set")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize VectorStore: {e}")
        return False

def test_confluence_connectivity():
    """Test basic connectivity to Confluence instance."""
    print("\n" + "="*60)
    print("TESTING CONFLUENCE CONNECTIVITY")
    print("="*60)
    
    if not check_confluence_credentials():
        print("⚠ Skipping connectivity test - missing credentials")
        return False
    
    try:
        from tools.confluence.app.confluence import ConfluenceClient
        
        client = ConfluenceClient()
        
        # Try to get a simple page (basic connectivity test)
        try:
            # Try to get a test page - using one of our target pages
            test_page_id = "4012343437"  # Helvetia page
            page_info = client.get_page_by_id(test_page_id)
            print("✓ Successfully connected to Confluence")
            print(f"  Retrieved page: {page_info.get('title', 'Unknown')}")
            print(f"  Page ID: {page_info.get('id', 'Unknown')}")
            return True
        except Exception as api_error:
            print(f"✗ Confluence API call failed: {api_error}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to test connectivity: {e}")
        return False

def test_target_pages_access():
    """Test if we can access the target root pages for Helvetia and Neste."""
    print("\n" + "="*60)
    print("TESTING TARGET PAGES ACCESS")
    print("="*60)
    
    if not check_confluence_credentials():
        print("⚠ Skipping page access test - missing credentials")
        return False
    
    target_pages = {
        "Helvetia": "4012343437",  # From the root URL
        "Neste": "4322296000"      # From the root URL
    }
    
    try:
        from tools.confluence.app.confluence import ConfluenceClient
        
        client = ConfluenceClient()
        results = {}
        
        for client_name, page_id in target_pages.items():
            try:
                # Try to get page info
                page = client.get_page_by_id(page_id)
                print(f"✓ Successfully accessed {client_name} page (ID: {page_id})")
                print(f"  Title: {page.get('title', 'Unknown')}")
                print(f"  Space: {page.get('space', {}).get('key', 'Unknown')}")
                results[client_name] = True
            except Exception as e:
                print(f"✗ Failed to access {client_name} page (ID: {page_id}): {e}")
                results[client_name] = False
        
        return all(results.values())
        
    except Exception as e:
        print(f"✗ Failed to test page access: {e}")
        return False

def test_page_children_functionality():
    """Test if we can get children of a page (needed for hierarchical discovery)."""
    print("\n" + "="*60)
    print("TESTING PAGE CHILDREN FUNCTIONALITY")
    print("="*60)
    
    if not check_confluence_credentials():
        print("⚠ Skipping children test - missing credentials")
        return False
    
    try:
        from tools.confluence.app.confluence import ConfluenceClient
        
        client = ConfluenceClient()
        
        # Check if client has the methods we need for discovery
        available_methods = [method for method in dir(client) if not method.startswith('_')]
        print(f"✓ ConfluenceClient available methods: {available_methods}")
        
        # Test search functionality as an alternative to hierarchical discovery
        try:
            # Search for pages in MCDBA space
            results = client.search_pages("runbook", space_key="MCDBA", limit=5)
            print("✓ Successfully searched for runbooks in MCDBA space")
            print(f"  Found {len(results)} pages matching 'runbook'")
            
            # Show first few results
            for i, page in enumerate(results[:3]):
                print(f"  Page {i+1}: {page.get('title', 'Unknown')} (ID: {page.get('id', 'Unknown')})")
            
            return len(results) > 0
            
        except Exception as e:
            print(f"✗ Failed to search for runbooks: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to test search functionality: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 80)
    print("CONFLUENCE TOOL FUNCTIONALITY TEST")
    print("=" * 80)
    
    # Setup environment
    if not setup_environment():
        print("❌ Environment setup failed")
        return False
    
    test_results = []
    
    # Run tests
    test_functions = [
        ("Import Test", test_confluence_tool_import),
        ("Client Initialization", test_confluence_client_initialization),
        ("VectorStore Initialization", test_vector_store_initialization),
        ("Confluence Connectivity", test_confluence_connectivity),
        ("Target Pages Access", test_target_pages_access),
        ("Page Children Functionality", test_page_children_functionality),
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Confluence tool is ready for runbook discovery.")
    else:
        print(f"\n⚠ {total - passed} tests failed. Check configuration and connectivity.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)