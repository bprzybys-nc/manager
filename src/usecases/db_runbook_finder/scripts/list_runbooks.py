#!/usr/bin/env python3
"""
List all runbooks in the mcdb-runbooks ChromaDB collection.

This script displays all discovered runbooks with their metadata and chunk counts.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add manager src to path and load environment
manager_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(manager_root / "src"))
load_dotenv(manager_root / ".env")

from tools.confluence.app.vector_store import VectorStore


def main():
    """List all runbooks in the collection."""
    try:
        # Initialize vector store
        vs = VectorStore(collection_name='mcdb-runbooks')
        
        # Get collection info
        collection = vs._collection
        count = collection.count()
        
        print('📚 ChromaDB Collection: mcdb-runbooks')
        print(f'📊 Total chunks: {count}')
        print('='*60)
        
        if count == 0:
            print("No runbooks found. Run discovery first:")
            print("uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks")
            return
        
        # Get all documents
        results = collection.get(limit=500)  # Should be enough for all runbooks
        
        # Group by runbook_id to show unique runbooks
        runbooks = {}
        for i, doc_id in enumerate(results['ids']):
            metadata = results['metadatas'][i]
            runbook_id = metadata.get('runbook_id', 'unknown')
            
            if runbook_id not in runbooks:
                tags = metadata.get('tags', [])
                client = 'Helvetia' if 'helvetia' in tags else 'Neste' if 'neste' in tags else 'Unknown'
                
                runbooks[runbook_id] = {
                    'title': metadata.get('title', 'Unknown'),
                    'page_id': metadata.get('page_id', 'Unknown'),
                    'client': client,
                    'chunks': 0,
                    'url': metadata.get('page_url', 'Unknown')
                }
            runbooks[runbook_id]['chunks'] += 1
        
        # Display runbooks grouped by client
        helvetia_runbooks = {k: v for k, v in runbooks.items() if v['client'] == 'Helvetia'}
        neste_runbooks = {k: v for k, v in runbooks.items() if v['client'] == 'Neste'}
        other_runbooks = {k: v for k, v in runbooks.items() if v['client'] == 'Unknown'}
        
        print(f'📝 Total unique runbooks: {len(runbooks)}')
        print()
        
        if helvetia_runbooks:
            print(f'🏢 HELVETIA RUNBOOKS ({len(helvetia_runbooks)}):')
            print('-' * 40)
            for i, (runbook_id, info) in enumerate(helvetia_runbooks.items(), 1):
                print(f'{i:2d}. {info["title"]}')
                print(f'    📄 Page ID: {info["page_id"]}')
                print(f'    🧩 Chunks: {info["chunks"]}')
                print(f'    🔗 URL: {info["url"]}')
                print()
        
        if neste_runbooks:
            print(f'🏢 NESTE RUNBOOKS ({len(neste_runbooks)}):')
            print('-' * 40)
            for i, (runbook_id, info) in enumerate(neste_runbooks.items(), 1):
                print(f'{i:2d}. {info["title"]}')
                print(f'    📄 Page ID: {info["page_id"]}')
                print(f'    🧩 Chunks: {info["chunks"]}')
                print(f'    🔗 URL: {info["url"]}')
                print()
        
        if other_runbooks:
            print(f'❓ OTHER RUNBOOKS ({len(other_runbooks)}):')
            print('-' * 40)
            for i, (runbook_id, info) in enumerate(other_runbooks.items(), 1):
                print(f'{i:2d}. {info["title"]}')
                print(f'    📄 Page ID: {info["page_id"]}')
                print(f'    🧩 Chunks: {info["chunks"]}')
                print(f'    🔗 URL: {info["url"]}')
                print()
        
        print('='*60)
        print(f'✅ Listed {len(runbooks)} runbooks from {count} total chunks')
        
    except Exception as e:
        print(f'❌ Error listing runbooks: {e}')
        print("\nTroubleshooting:")
        print("1. Make sure ChromaDB is accessible")
        print("2. Run discovery first if collection is empty")
        print("3. Check .env file for proper configuration")
        sys.exit(1)


if __name__ == "__main__":
    main()