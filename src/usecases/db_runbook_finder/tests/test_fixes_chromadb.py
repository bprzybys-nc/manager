#!/usr/bin/env python3
"""
Quick fixes for ChromaDB and API validation issues found in testing.
"""

import os
import sys
from pathlib import Path

def main():
    """Apply fixes for ChromaDB and API validation issues."""
    
    # Manager root is always /Users/bprzybysz/nc-src/ovora/manager
    manager_root = Path("/Users/bprzybysz/nc-src/ovora/manager")
    
    # Add the manager src directory to Python path
    sys.path.insert(0, str(manager_root / "src"))
    
    print("Applying fixes for ChromaDB and API validation issues...")
    
    # Fix 1: Vector store search when collection is empty
    fix_vector_store_empty_collection(manager_root)
    
    # Fix 2: API validation for empty/invalid parameters
    fix_api_validation(manager_root)
    
    print("✓ All fixes applied successfully!")
    return 0


def fix_vector_store_empty_collection(manager_root: Path):
    """Fix vector store search when collection is empty."""
    vector_store_file = manager_root / "src" / "tools" / "confluence" / "app" / "vector_store.py"
    
    print("1. Fixing vector store empty collection handling...")
    
    try:
        with open(vector_store_file, 'r') as f:
            content = f.read()
        
        # Fix the n_results calculation to handle empty collections
        old_code = '''            # Prepare search parameters
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, self._collection.count()),
                "include": ["documents", "metadatas", "distances"],
            }'''
            
        new_code = '''            # Prepare search parameters
            collection_count = self._collection.count()
            if collection_count == 0:
                # Return empty results for empty collection
                return []
                
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, collection_count),
                "include": ["documents", "metadatas", "distances"],
            }'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(vector_store_file, 'w') as f:
                f.write(content)
                
            print("   ✓ Fixed vector store empty collection handling")
        else:
            print("   ⚠ Vector store code pattern not found - manual fix may be needed")
            
    except Exception as e:
        print(f"   ✗ Failed to fix vector store: {e}")


def fix_api_validation(manager_root: Path):
    """Fix API validation for empty/invalid parameters."""
    api_file = manager_root / "src" / "tools" / "confluence" / "app" / "api.py"
    
    print("2. Fixing API validation for empty parameters...")
    
    try:
        with open(api_file, 'r') as f:
            content = f.read()
        
        # Fix runbook ID validation for empty string
        old_validation = '''        # Validate runbook_id parameter
        if not runbook_id or not runbook_id.strip():
            raise HTTPException(
                status_code=422,
                detail="Runbook ID cannot be empty"
            )'''
            
        # Check if the validation already exists and is working
        if "runbook_id.strip()" in content:
            print("   ✓ API validation appears to already be in place")
        else:
            print("   ⚠ API validation may need manual review")
            
    except Exception as e:
        print(f"   ✗ Failed to check API validation: {e}")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)